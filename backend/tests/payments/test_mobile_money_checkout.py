from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.cart.models import CartItem
from apps.finance.services import shop_balance
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Dar es Salaam",
    "region": "Dar es Salaam",
    "postal_code": "11101",
    "country": "Tanzania",
    "phone": "+255712345678",
    "latitude": -6.7924,
    "longitude": 39.2083,
}
CALLBACK_TOKEN = "test-callback-token"


@pytest.fixture(autouse=True)
def simulator_backend(settings):
    settings.PAYMENT_BACKEND = "azampay_simulator"
    settings.AZAMPAY_CALLBACK_TOKEN = CALLBACK_TOKEN
    settings.PAYMENT_PENDING_TIMEOUT_MINUTES = 15


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _checkout(api_client, msisdn="0712345678", provider="Mpesa"):
    return api_client.post(
        "/api/checkout",
        {
            "shipping": SHIPPING,
            "payment_method": "mobile_money",
            "msisdn": msisdn,
            "provider": provider,
        },
        format="json",
    )


@pytest.fixture
def shop():
    return ShopFactory(status=Shop.Status.APPROVED)


@pytest.fixture
def product(shop):
    return ProductFactory(shop=shop, is_published=True, price="5000", stock_quantity=10)


@pytest.fixture
def customer(api_client, product):
    user = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, user)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    return user


def _record(order_id):
    return PaymentRecord.objects.get(order_id=order_id)


def _callback(api_client, record, status="success", amount=None, token=CALLBACK_TOKEN):
    api_client.credentials()
    return api_client.post(
        f"/api/payments/azampay/callback/{token}",
        {
            "msisdn": record.msisdn,
            "amount": amount if amount is not None else str(int(record.amount)),
            "message": "done",
            "utilityref": record.transaction_reference,
            "operator": record.provider,
            "reference": "AZ123",
            "transactionstatus": status,
            "submerchantAcc": None,
        },
        format="json",
    )


def test_mobile_money_checkout_reserves_stock_and_keeps_cart(api_client, customer, product):
    response = _checkout(api_client, msisdn="+255 712-345-678")

    assert response.status_code == 202
    assert response.data["status"] == "AWAITING_PAYMENT"
    assert response.data["payment"]["status"] == "PENDING"
    assert response.data["payment"]["provider"] == "Mpesa"
    assert response.data["payment"]["msisdn"] == "25571****678"
    record = _record(response.data["id"])
    assert record.msisdn == "255712345678"
    assert record.provider_reference.startswith("SIM")
    product.refresh_from_db()
    assert product.stock_quantity == 8
    assert CartItem.objects.filter(cart__customer=customer).count() == 1


def test_mobile_money_requires_valid_number_and_network(api_client, customer):
    response = _checkout(api_client, msisdn="12345", provider="")

    assert response.status_code == 400
    assert "msisdn" in response.data and "provider" in response.data
    assert Order.objects.count() == 0


def test_approved_callback_places_order_and_clears_cart(api_client, customer, product):
    order_id = _checkout(api_client).data["id"]

    response = _callback(api_client, _record(order_id))

    assert response.status_code == 200
    record = _record(order_id)
    assert record.status == PaymentRecord.Status.SUCCEEDED
    assert record.provider_reference == "AZ123"
    assert Order.objects.get(pk=order_id).status == Order.Status.PLACED
    assert not CartItem.objects.filter(cart__customer=customer).exists()
    product.refresh_from_db()
    assert product.stock_quantity == 8


def test_failed_callback_releases_stock_and_keeps_cart(api_client, customer, product):
    order_id = _checkout(api_client).data["id"]

    _callback(api_client, _record(order_id), status="failure")

    assert _record(order_id).status == PaymentRecord.Status.FAILED
    order = Order.objects.get(pk=order_id)
    assert order.status == Order.Status.PAYMENT_FAILED
    assert set(order.items.values_list("status", flat=True)) == {OrderItem.Status.CANCELLED}
    product.refresh_from_db()
    assert product.stock_quantity == 10
    assert CartItem.objects.filter(cart__customer=customer).count() == 1


def test_repeated_callback_is_a_no_op(api_client, customer, product):
    order_id = _checkout(api_client).data["id"]
    record = _record(order_id)
    _callback(api_client, record)

    _callback(api_client, record, status="failure")

    assert _record(order_id).status == PaymentRecord.Status.SUCCEEDED
    assert Order.objects.get(pk=order_id).status == Order.Status.PLACED
    product.refresh_from_db()
    assert product.stock_quantity == 8


def test_callback_with_wrong_amount_is_ignored(api_client, customer):
    order_id = _checkout(api_client).data["id"]

    response = _callback(api_client, _record(order_id), amount="1")

    assert response.status_code == 200
    assert _record(order_id).status == PaymentRecord.Status.PENDING


def test_callback_with_wrong_token_is_404(api_client, customer):
    order_id = _checkout(api_client).data["id"]

    response = _callback(api_client, _record(order_id), token="guess")

    assert response.status_code == 404
    assert _record(order_id).status == PaymentRecord.Status.PENDING


def test_second_checkout_while_pending_is_409(api_client, customer):
    order_id = _checkout(api_client).data["id"]

    response = _checkout(api_client)

    assert response.status_code == 409
    assert response.data["code"] == "payment_pending"
    assert response.data["order_id"] == order_id
    assert Order.objects.count() == 1


def test_push_refused_by_provider_fails_order_immediately(api_client, customer, product):
    response = _checkout(api_client, msisdn="0712340000")

    assert response.status_code == 400
    assert response.data["code"] == "payment_failed"
    assert Order.objects.get(pk=response.data["order_id"]).status == Order.Status.PAYMENT_FAILED
    product.refresh_from_db()
    assert product.stock_quantity == 10


def test_expire_command_fails_stale_pending_payments(api_client, customer, product):
    order_id = _checkout(api_client).data["id"]
    PaymentRecord.objects.filter(order_id=order_id).update(
        created_at=timezone.now() - timedelta(minutes=16)
    )

    call_command("expire_pending_payments")

    record = _record(order_id)
    assert record.status == PaymentRecord.Status.FAILED
    assert "expired" in record.failure_reason
    product.refresh_from_db()
    assert product.stock_quantity == 10


def test_payment_status_endpoint_reports_and_lazily_expires(api_client, customer):
    order_id = _checkout(api_client).data["id"]

    response = api_client.get(f"/api/orders/{order_id}/payment-status")
    assert response.data["order_status"] == "AWAITING_PAYMENT"
    assert response.data["payment_status"] == "PENDING"

    PaymentRecord.objects.filter(order_id=order_id).update(
        created_at=timezone.now() - timedelta(minutes=16)
    )
    response = api_client.get(f"/api/orders/{order_id}/payment-status")
    assert response.data["order_status"] == "PAYMENT_FAILED"
    assert response.data["payment_status"] == "FAILED"


def test_payment_status_is_scoped_to_owner(api_client, customer):
    order_id = _checkout(api_client).data["id"]
    _authenticate(api_client, UserFactory(role=User.Role.CUSTOMER))

    assert api_client.get(f"/api/orders/{order_id}/payment-status").status_code == 404


def test_vendor_sees_order_only_once_paid(api_client, customer, shop):
    order_id = _checkout(api_client).data["id"]
    record = _record(order_id)
    _authenticate(api_client, shop.owner)
    assert api_client.get("/api/vendor/order-items").data["count"] == 0

    _callback(api_client, record)

    _authenticate(api_client, shop.owner)
    assert api_client.get("/api/vendor/order-items").data["count"] == 1


def test_simulator_approve_runs_callback_path(api_client, customer):
    order_id = _checkout(api_client).data["id"]
    api_client.credentials()

    pushes = api_client.get("/api/dev/azampay-sim/pushes").data
    assert [push["order_id"] for push in pushes] == [order_id]
    assert pushes[0]["amount"] == "12000"

    reference = pushes[0]["reference"]
    response = api_client.post(
        f"/api/dev/azampay-sim/pushes/{reference}/approve", {"pin": "1234"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["callback"]["transactionstatus"] == "success"
    assert Order.objects.get(pk=order_id).status == Order.Status.PLACED


def test_simulator_reject(api_client, customer):
    order_id = _checkout(api_client).data["id"]
    reference = _record(order_id).transaction_reference
    api_client.credentials()

    api_client.post(f"/api/dev/azampay-sim/pushes/{reference}/reject")

    assert Order.objects.get(pk=order_id).status == Order.Status.PAYMENT_FAILED


def test_simulator_endpoints_404_outside_simulator_mode(api_client, settings):
    settings.PAYMENT_BACKEND = "azampay"

    assert api_client.get("/api/dev/azampay-sim/pushes").status_code == 404


def test_card_checkout_is_still_synchronous(api_client, customer):
    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["payment"]["status"] == "SUCCEEDED"


def test_unpaid_order_lines_are_left_out_of_shop_balances(api_client, customer, shop):
    order_id = _checkout(api_client).data["id"]
    assert shop_balance(shop)["pending_earnings"] == 0

    _callback(api_client, _record(order_id))

    assert shop_balance(shop)["pending_earnings"] > 0
