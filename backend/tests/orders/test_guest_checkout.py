"""Guest checkout: buying without an account, and following the order by its private link."""

import pytest
from django.core import mail
from rest_framework.test import APIClient

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


@pytest.fixture
def product():
    return ProductFactory(is_published=True, price="5000", stock_quantity=10)


@pytest.fixture
def guest(api_client, product):
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    return api_client


def _checkout(client, **extra):
    body = {"shipping": SHIPPING, "payment_method": "card", "email": "ama@example.com"}
    body.update(extra)
    return client.post("/api/checkout", body, format="json")


def test_guest_checkout_places_order(guest, product, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = _checkout(guest)

    assert response.status_code == 201
    token = response.data["access_token"]
    order = Order.objects.get(pk=response.data["id"])
    assert order.status == Order.Status.PLACED
    assert order.customer is None
    assert order.guest_email == "ama@example.com"
    assert order.access_token == token
    assert PaymentRecord.objects.get(order=order).status == PaymentRecord.Status.SUCCEEDED
    assert not CartItem.objects.exists()
    product.refresh_from_db()
    assert product.stock_quantity == 8

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ama@example.com"]
    assert f"/orders/track/{token}" in mail.outbox[0].body


def test_guest_checkout_requires_email(guest):
    response = _checkout(guest, email="")

    assert response.status_code == 400
    assert "email" in response.data
    assert Order.objects.count() == 0


def test_guest_without_cart_gets_empty_cart(api_client):
    response = _checkout(api_client)

    assert response.status_code == 400
    assert Order.objects.count() == 0


def test_track_endpoints_need_the_right_token(guest):
    token = _checkout(guest).data["access_token"]
    stranger = APIClient()

    detail = stranger.get(f"/api/orders/track/{token}")
    assert detail.status_code == 200
    assert detail.data["status"] == "PLACED"
    assert detail.data["access_token"] == token

    status = stranger.get(f"/api/orders/track/{token}/payment-status")
    assert status.status_code == 200
    assert status.data["payment_status"] == "SUCCEEDED"

    assert stranger.get("/api/orders/track/not-the-token").status_code == 404
    assert stranger.get("/api/orders/track/not-the-token/payment-status").status_code == 404


def test_guest_order_not_reachable_by_id(guest):
    order_id = _checkout(guest).data["id"]

    assert guest.get(f"/api/orders/{order_id}").status_code == 401


def test_customer_checkout_response_has_no_access_token(api_client, product):
    from apps.accounts.models import User
    from tests.factories import UserFactory

    customer = UserFactory(role=User.Role.CUSTOMER)
    api_client.force_authenticate(customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")

    response = _checkout(api_client, email="")

    assert response.status_code == 201
    assert "access_token" not in response.data
    assert Order.objects.get().customer == customer


def test_admin_sees_guest_buyer(guest):
    from apps.accounts.models import User
    from tests.factories import UserFactory

    order_id = _checkout(guest).data["id"]
    admin = APIClient()
    admin.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))

    transactions = admin.get("/api/admin/transactions", {"search": "ama@example"})
    assert transactions.status_code == 200
    row = transactions.data["results"][0]
    assert row["order_id"] == order_id
    assert row["customer"] == {
        "id": None,
        "name": "Ama Owusu",
        "email": "ama@example.com",
        "is_guest": True,
    }
