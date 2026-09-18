import pytest

from apps.accounts.models import User
from apps.cart.models import CartItem
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_add_to_cart_creates_line_with_correct_subtotal(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    _authenticate(api_client, customer)

    response = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )

    assert response.status_code == 201
    assert response.data["quantity"] == 2
    assert response.data["unit_price"] == "9.99"
    assert response.data["subtotal"] == "19.98"


def test_add_to_cart_rejects_quantity_below_one(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, stock_quantity=10)
    _authenticate(api_client, customer)

    response = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 0}, format="json"
    )

    assert response.status_code == 400
    assert CartItem.objects.count() == 0


def test_add_to_cart_rejects_quantity_above_available_stock(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, stock_quantity=3)
    _authenticate(api_client, customer)

    response = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 4}, format="json"
    )

    assert response.status_code == 400
    assert "3" in str(response.data["quantity"])
    assert CartItem.objects.count() == 0


def test_add_to_cart_rejects_unpublished_product(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=False, stock_quantity=10)
    _authenticate(api_client, customer)

    response = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )

    assert response.status_code == 400
    assert CartItem.objects.count() == 0
