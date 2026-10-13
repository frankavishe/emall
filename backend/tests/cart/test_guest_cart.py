"""Guest checkout: anonymous visitors get a server-side cart found through an httpOnly cookie."""

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.models import Cart, CartItem
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _add(client, product, quantity=1):
    return client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
    )


def test_anonymous_add_creates_guest_cart_and_sets_cookie(api_client):
    product = ProductFactory(is_published=True)

    response = _add(api_client, product, 2)

    assert response.status_code == 201
    cookie = response.cookies[settings.GUEST_CART_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["path"] == settings.GUEST_CART_COOKIE_PATH
    cart = Cart.objects.get(guest_token=cookie.value)
    assert cart.customer is None
    assert cart.items.get().quantity == 2


def test_cookie_carries_the_guest_cart_across_requests(api_client):
    product = ProductFactory(is_published=True, stock_quantity=10)
    _add(api_client, product, 1)
    _add(api_client, product, 2)

    response = api_client.get("/api/cart")

    assert response.status_code == 200
    assert len(response.data["items"]) == 1
    assert response.data["items"][0]["quantity"] == 3
    assert Cart.objects.count() == 1


def test_guest_cannot_touch_another_guests_line(api_client):
    product = ProductFactory(is_published=True)
    _add(api_client, product)
    item = CartItem.objects.get()

    other_guest = APIClient()
    _add(other_guest, ProductFactory(is_published=True))

    assert other_guest.patch(
        f"/api/cart/items/{item.id}", {"quantity": 2}, format="json"
    ).status_code == 404
    assert other_guest.delete(f"/api/cart/items/{item.id}").status_code == 404
    assert APIClient().delete(f"/api/cart/items/{item.id}").status_code == 404


def test_signed_in_non_shopper_still_refused(api_client):
    # Riders can't shop; being signed in must not fall back to guest access.
    api_client.force_authenticate(UserFactory(role=User.Role.RIDER))

    assert api_client.get("/api/cart").status_code == 403


def test_login_merges_guest_cart_capped_at_stock(api_client):
    shared = ProductFactory(is_published=True, stock_quantity=5)
    guest_only = ProductFactory(is_published=True, stock_quantity=5)
    customer = UserFactory(role=User.Role.CUSTOMER)
    customer_cart = Cart.objects.create(customer=customer)
    CartItem.objects.create(cart=customer_cart, product=shared, quantity=4)

    _add(api_client, shared, 3)
    _add(api_client, guest_only, 2)

    response = api_client.post(
        "/api/auth/login",
        {"email": customer.email, "password": "a-strong-password-1"},
        format="json",
    )

    assert response.status_code == 200
    assert response.cookies[settings.GUEST_CART_COOKIE_NAME].value == ""
    quantities = {item.product_id: item.quantity for item in customer_cart.items.all()}
    assert quantities == {shared.id: 5, guest_only.id: 2}
    assert not Cart.objects.filter(customer__isnull=True).exists()
