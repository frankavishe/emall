import pytest

from apps.accounts.models import User
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_cart_persists_across_separate_authenticated_sessions(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product_a = ProductFactory(is_published=True, stock_quantity=10)
    product_b = ProductFactory(is_published=True, stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product_a.id, "quantity": 2}, format="json")
    api_client.post("/api/cart/items", {"product_id": product_b.id, "quantity": 1}, format="json")

    # Simulate a fresh login (new client, new token) rather than reusing credentials.
    from rest_framework.test import APIClient

    fresh_client = APIClient()
    _authenticate(fresh_client, customer)
    response = fresh_client.get("/api/cart")

    assert response.status_code == 200
    quantities = {item["product"]["id"]: item["quantity"] for item in response.data["items"]}
    assert quantities == {product_a.id: 2, product_b.id: 1}
