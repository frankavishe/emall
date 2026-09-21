import pytest

from apps.accounts.models import User
from apps.orders.models import Order
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_checkout_rejects_missing_shipping_field(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=5)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )
    shipping = {
        "recipient_name": "Ama Owusu",
        "address_line": "12 Ring Road",
        "city": "Accra",
        "region": "Greater Accra",
        "country": "Ghana",
        "phone": "+233201234567",
    }  # postal_code omitted

    response = api_client.post(
        "/api/checkout", {"shipping": shipping, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 400
    assert "postal_code" in response.data["shipping"]
    assert Order.objects.count() == 0


def test_checkout_rejects_blank_shipping_field(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=5)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )
    shipping = {
        "recipient_name": "",
        "address_line": "12 Ring Road",
        "city": "Accra",
        "region": "Greater Accra",
        "postal_code": "GA-184-9021",
        "country": "Ghana",
        "phone": "+233201234567",
    }

    response = api_client.post(
        "/api/checkout", {"shipping": shipping, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 400
    assert "recipient_name" in response.data["shipping"]
    assert Order.objects.count() == 0
