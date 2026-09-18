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


def test_adding_same_product_twice_merges_into_one_line(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, stock_quantity=10)
    _authenticate(api_client, customer)

    first = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )
    second = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert CartItem.objects.filter(product=product).count() == 1
    assert CartItem.objects.get(product=product).quantity == 3


def test_merged_quantity_still_validated_against_stock(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, stock_quantity=3)
    _authenticate(api_client, customer)

    first = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )
    second = api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )

    assert first.status_code == 201
    assert second.status_code == 400
    assert CartItem.objects.get(product=product).quantity == 2
