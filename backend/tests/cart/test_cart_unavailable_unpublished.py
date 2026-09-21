import pytest

from apps.accounts.models import User
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_cart_flags_line_unavailable_when_product_unpublished(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    available_product = ProductFactory(is_published=True, price="5.00", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    api_client.post(
        "/api/cart/items", {"product_id": available_product.id, "quantity": 1}, format="json"
    )

    product.is_published = False
    product.save(update_fields=["is_published"])

    response = api_client.get("/api/cart")

    assert response.status_code == 200
    items_by_product = {item["product"]["id"]: item for item in response.data["items"]}
    unavailable_item = items_by_product[product.id]
    assert unavailable_item["is_available"] is False
    assert unavailable_item["unavailable_reason"] == "no longer published"
    available_item = items_by_product[available_product.id]
    assert available_item["is_available"] is True
    # Only the still-available line contributes to the total.
    assert response.data["total"] == "5.00"
