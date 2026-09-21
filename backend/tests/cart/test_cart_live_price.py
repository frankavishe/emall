import pytest

from apps.accounts.models import User
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_cart_reflects_price_change_after_add(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")

    product.price = "14.50"
    product.save(update_fields=["price"])

    response = api_client.get("/api/cart")

    assert response.status_code == 200
    item = response.data["items"][0]
    assert item["unit_price"] == "14.50"
    assert item["subtotal"] == "29.00"
    assert response.data["total"] == "29.00"
