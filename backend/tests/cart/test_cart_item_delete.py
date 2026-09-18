import pytest

from apps.accounts.models import User
from apps.cart.models import CartItem
from tests.factories import CartFactory, CartItemFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_delete_removes_only_that_line(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    cart = CartFactory(customer=customer)
    keep = CartItemFactory(cart=cart)
    remove = CartItemFactory(cart=cart)
    _authenticate(api_client, customer)

    response = api_client.delete(f"/api/cart/items/{remove.id}")

    assert response.status_code == 204
    assert not CartItem.objects.filter(pk=remove.pk).exists()
    assert CartItem.objects.filter(pk=keep.pk).exists()


def test_delete_another_customers_line_is_not_found(api_client):
    owner = UserFactory(role=User.Role.CUSTOMER)
    other = UserFactory(role=User.Role.CUSTOMER)
    item = CartItemFactory(cart__customer=owner)
    _authenticate(api_client, other)

    response = api_client.delete(f"/api/cart/items/{item.id}")

    assert response.status_code == 404
    assert CartItem.objects.filter(pk=item.pk).exists()
