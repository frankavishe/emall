import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_owner_can_update_a_draft_product(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=False)
    _authenticate(api_client, vendor)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}", {"price": "19.99"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["price"] == "19.99"


def test_owner_can_update_a_published_product(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    _authenticate(api_client, vendor)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}", {"stock_quantity": 5}, format="json"
    )

    assert response.status_code == 200
    assert response.data["stock_quantity"] == 5


def test_non_owner_cannot_update_product(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    other_vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=other_vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop)
    _authenticate(api_client, vendor)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}", {"price": "1.00"}, format="json"
    )

    assert response.status_code == 403
