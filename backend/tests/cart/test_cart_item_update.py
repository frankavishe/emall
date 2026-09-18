import pytest

from apps.accounts.models import User
from tests.factories import CartItemFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_update_quantity_recalculates_subtotal(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    item = CartItemFactory(cart__customer=customer, product=product, quantity=2)
    _authenticate(api_client, customer)

    response = api_client.patch(
        f"/api/cart/items/{item.id}", {"quantity": 5}, format="json"
    )

    assert response.status_code == 200
    assert response.data["quantity"] == 5
    assert response.data["subtotal"] == "49.95"


def test_update_quantity_rejects_above_stock(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, stock_quantity=3)
    item = CartItemFactory(cart__customer=customer, product=product, quantity=2)
    _authenticate(api_client, customer)

    response = api_client.patch(
        f"/api/cart/items/{item.id}", {"quantity": 4}, format="json"
    )

    assert response.status_code == 400
    item.refresh_from_db()
    assert item.quantity == 2


def test_update_another_customers_line_is_not_found(api_client):
    owner = UserFactory(role=User.Role.CUSTOMER)
    other = UserFactory(role=User.Role.CUSTOMER)
    item = CartItemFactory(cart__customer=owner)
    _authenticate(api_client, other)

    response = api_client.patch(
        f"/api/cart/items/{item.id}", {"quantity": 1}, format="json"
    )

    assert response.status_code == 404
