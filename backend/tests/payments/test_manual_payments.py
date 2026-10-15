"""Cash on delivery and Lipa Namba: payments with no gateway, settled by an administrator."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
from apps.payments.outcomes import expire_stale_payments
from apps.vendors.models import Shop
from tests.factories import ProductFactory, UserFactory

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


@pytest.fixture
def product():
    return ProductFactory(
        is_published=True,
        price="5000",
        stock_quantity=10,
        shop__payout_network=Shop.PayoutNetwork.MPESA,
        shop__payout_phone="+255712345678",
        shop__payout_account_name="Juma Shop",
    )


@pytest.fixture
def guest(api_client, product):
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    return api_client


@pytest.fixture
def admin(api_client):
    return UserFactory(role=User.Role.ADMINISTRATOR)


def _checkout(client, method, **extra):
    return client.post(
        "/api/checkout",
        {"shipping": SHIPPING, "payment_method": method, "email": "ama@example.com", **extra},
        format="json",
    )


def _as(client, user):
    client.force_authenticate(user)
    return client


def _settle(client, order_id, action, **body):
    return client.post(f"/api/admin/orders/{order_id}/payment/{action}", body, format="json")


def _vendor_sees(client, product):
    _as(client, product.shop.owner)
    data = client.get("/api/vendor/order-items").data
    rows = data["results"] if isinstance(data, dict) else data
    return len(rows) > 0


# --- Payment methods --------------------------------------------------------------------------


def test_methods_lists_enabled_manual_methods_with_till(api_client, settings):
    methods = {m["method"]: m for m in api_client.get("/api/payments/methods").data}
    assert {"cod", "lipa_namba"} <= set(methods)
    assert methods["lipa_namba"]["till_number"] == "123456"

    settings.MANUAL_PAYMENT_METHODS = []
    settings.MOCK_CARD_PAYMENTS_ENABLED = False
    assert api_client.get("/api/payments/methods").data == []


def test_lipa_namba_needs_a_till(guest, api_client, settings):
    settings.LIPA_NAMBA_TILL = ""
    methods = [m["method"] for m in api_client.get("/api/payments/methods").data]
    assert "lipa_namba" not in methods
    assert _checkout(guest, "lipa_namba", payer_reference="ABC123").status_code == 400


def test_disabled_methods_are_rejected(guest, settings):
    settings.MANUAL_PAYMENT_METHODS = []
    settings.MOCK_CARD_PAYMENTS_ENABLED = False
    for method in ("cod", "lipa_namba", "card", "mobile_money"):
        response = _checkout(guest, method, payer_reference="ABC123")
        assert response.status_code == 400, method
        assert "payment_method" in response.data
    assert not Order.objects.exists()


# --- Cash on delivery -------------------------------------------------------------------------


def test_cod_order_is_placed_with_payment_due(guest, product, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = _checkout(guest, "cod")

    assert response.status_code == 201
    order = Order.objects.get()
    assert order.status == Order.Status.PLACED
    assert order.payment.method == "cod"
    assert order.payment.status == PaymentRecord.Status.PENDING
    assert response.data["payment"]["status"] == "PENDING"
    assert not CartItem.objects.exists()
    product.refresh_from_db()
    assert product.stock_quantity == 8
    assert "cash on delivery" in mail.outbox[0].body
    assert _vendor_sees(guest, product)


def test_cod_never_expires(guest):
    _checkout(guest, "cod")
    PaymentRecord.objects.update(created_at=timezone.now() - timedelta(days=30))

    assert expire_stale_payments() == 0
    assert PaymentRecord.objects.get().status == PaymentRecord.Status.PENDING


def test_admin_confirms_cod_cash(guest, admin):
    _checkout(guest, "cod")
    order = Order.objects.get()

    response = _settle(_as(guest, admin), order.id, "confirm")

    assert response.status_code == 200
    assert response.data["payment"]["status"] == "SUCCEEDED"
    assert response.data["payment"]["settled_by"] == admin.name
    order.refresh_from_db()
    assert order.status == Order.Status.PLACED
    assert order.payment.settled_by == admin
    assert order.payment.settled_at is not None

    # Settling twice is refused rather than repeated.
    assert _settle(guest, order.id, "confirm").status_code == 400


def test_delivered_cod_line_is_not_paid_out_until_cash_confirmed(guest, admin, product):
    _checkout(guest, "cod")
    order = Order.objects.get()
    order.items.update(status=OrderItem.Status.DELIVERED)
    _as(guest, admin)

    balance = guest.get(f"/api/admin/shops/{product.shop_id}").data["balance"]
    assert balance["available_balance"] == "0.00"
    assert guest.post(f"/api/admin/shops/{product.shop_id}/payouts").status_code == 400

    _settle(guest, order.id, "confirm")

    balance = guest.get(f"/api/admin/shops/{product.shop_id}").data["balance"]
    assert balance["available_balance"] != "0.00"
    assert guest.post(f"/api/admin/shops/{product.shop_id}/payouts").status_code == 201


# --- Lipa Namba -------------------------------------------------------------------------------


def test_lipa_namba_requires_transaction_id(guest):
    response = _checkout(guest, "lipa_namba")

    assert response.status_code == 400
    assert "payer_reference" in response.data
    assert not Order.objects.exists()


def test_lipa_namba_waits_for_admin(guest, product):
    response = _checkout(guest, "lipa_namba", payer_reference="  QJK7H2LM9P ")

    assert response.status_code == 202
    order = Order.objects.get()
    assert order.status == Order.Status.AWAITING_PAYMENT
    assert order.payment.provider_reference == "QJK7H2LM9P"
    assert response.data["payment"]["payer_reference"] == "QJK7H2LM9P"
    assert CartItem.objects.exists()  # kept until the payment is confirmed
    assert not _vendor_sees(guest, product)


def test_admin_confirms_lipa_namba(guest, admin, product, django_capture_on_commit_callbacks):
    _checkout(guest, "lipa_namba", payer_reference="QJK7H2LM9P")
    order = Order.objects.get()

    with django_capture_on_commit_callbacks(execute=True):
        response = _settle(_as(guest, admin), order.id, "confirm")

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PLACED
    assert order.payment.status == PaymentRecord.Status.SUCCEEDED
    assert not CartItem.objects.exists()
    assert "Payment received" in mail.outbox[0].body
    assert _vendor_sees(guest, product)


def test_admin_rejects_lipa_namba(guest, admin, product):
    _checkout(guest, "lipa_namba", payer_reference="NOTREAL")
    order = Order.objects.get()

    response = _settle(_as(guest, admin), order.id, "reject", reason="No such transaction.")

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED
    assert order.payment.status == PaymentRecord.Status.FAILED
    assert order.payment.failure_reason == "No such transaction."
    product.refresh_from_db()
    assert product.stock_quantity == 10


def test_lipa_namba_expires_after_manual_timeout(guest, settings):
    settings.MANUAL_PAYMENT_TIMEOUT_HOURS = 24
    _checkout(guest, "lipa_namba", payer_reference="QJK7H2LM9P")

    # Older than the mobile-money timeout but within a day: left alone.
    PaymentRecord.objects.update(created_at=timezone.now() - timedelta(hours=2))
    assert expire_stale_payments() == 0

    PaymentRecord.objects.update(created_at=timezone.now() - timedelta(hours=25))
    assert expire_stale_payments() == 1
    assert Order.objects.get().status == Order.Status.PAYMENT_FAILED


def test_pending_payments_queue(guest, admin):
    _checkout(guest, "lipa_namba", payer_reference="QJK7H2LM9P")
    _as(guest, admin)

    rows = guest.get("/api/admin/transactions?status=PENDING&method=lipa_namba").data["results"]
    assert [row["provider_reference"] for row in rows] == ["QJK7H2LM9P"]
    assert guest.get("/api/admin/transactions?search=QJK7H2").data["count"] == 1
    assert guest.get("/api/admin/transactions?status=SUCCEEDED").data["count"] == 0


# --- Access -----------------------------------------------------------------------------------


def test_only_admins_settle(guest, product):
    _checkout(guest, "cod")
    order = Order.objects.get()

    assert _settle(guest, order.id, "confirm").status_code in (401, 403)
    assert _settle(_as(guest, product.shop.owner), order.id, "confirm").status_code == 403
    assert Order.objects.get().payment.status == PaymentRecord.Status.PENDING


def test_card_payments_cannot_be_settled_by_hand(guest, admin):
    _checkout(guest, "card")
    order = Order.objects.get()

    response = _settle(_as(guest, admin), order.id, "reject")

    assert response.status_code == 400
    assert Order.objects.get().status == Order.Status.PLACED
