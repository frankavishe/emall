import pytest
from django.core import mail

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

# `transaction=True` is required: `transaction.on_commit()` callbacks (research.md §1) only fire
# on a real commit, which pytest-django's default savepoint-wrapped test transaction never
# performs.
pytestmark = pytest.mark.django_db(transaction=True)

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Accra",
    "region": "Greater Accra",
    "postal_code": "GA-184-9021",
    "country": "Ghana",
    "phone": "+233201234567",
}


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_advancing_to_processing_sends_one_email(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )
    checkout_response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    order_id = checkout_response.data["id"]

    _authenticate(api_client, vendor)
    item_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]
    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "PROCESSING"}, format="json"
    )
    assert response.status_code == 200

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [customer.email]
    assert email.subject == "Your order is being prepared"
    assert str(order_id) in email.body
    assert product.name in email.body
