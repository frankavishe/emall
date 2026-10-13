"""Guest checkout paid by mobile money (AzamPay simulator backend)."""

import pytest
from django.core import mail

from apps.cart.models import CartItem
from apps.orders.models import Order
from apps.payments.models import PaymentRecord
from tests.factories import ProductFactory

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


@pytest.fixture
def product():
    return ProductFactory(is_published=True, price="5000", stock_quantity=10)


@pytest.fixture
def guest(api_client, product):
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    return api_client


def _checkout(client):
    return client.post(
        "/api/checkout",
        {
            "shipping": SHIPPING,
            "payment_method": "mobile_money",
            "msisdn": "0712345678",
            "provider": "Mpesa",
            "email": "ama@example.com",
        },
        format="json",
    )


def _callback(client, record, status="success"):
    return client.post(
        f"/api/payments/azampay/callback/{CALLBACK_TOKEN}",
        {
            "msisdn": record.msisdn,
            "amount": str(int(record.amount)),
            "message": "done",
            "utilityref": record.transaction_reference,
            "operator": record.provider,
            "reference": "AZ123",
            "transactionstatus": status,
            "submerchantAcc": None,
        },
        format="json",
    )


def test_guest_mobile_money_awaits_payment_and_blocks_second_checkout(guest):
    first = _checkout(guest)

    assert first.status_code == 202
    assert first.data["status"] == "AWAITING_PAYMENT"
    token = first.data["access_token"]
    assert CartItem.objects.count() == 1

    second = _checkout(guest)
    assert second.status_code == 409
    assert second.data["code"] == "payment_pending"
    assert second.data["access_token"] == token
    assert "order_id" not in second.data


def test_approved_callback_clears_guest_cart_and_emails(
    guest, product, django_capture_on_commit_callbacks
):
    order_id = _checkout(guest).data["id"]
    record = PaymentRecord.objects.get(order_id=order_id)

    with django_capture_on_commit_callbacks(execute=True):
        assert _callback(guest, record).status_code == 200

    order = Order.objects.get(pk=order_id)
    assert order.status == Order.Status.PLACED
    assert not CartItem.objects.exists()
    assert len(mail.outbox) == 1
    assert f"/orders/track/{order.access_token}" in mail.outbox[0].body


def test_failed_callback_releases_stock_and_keeps_guest_cart(guest, product):
    order_id = _checkout(guest).data["id"]
    record = PaymentRecord.objects.get(order_id=order_id)

    _callback(guest, record, status="failure")

    assert Order.objects.get(pk=order_id).status == Order.Status.PAYMENT_FAILED
    assert CartItem.objects.count() == 1
    product.refresh_from_db()
    assert product.stock_quantity == 10
