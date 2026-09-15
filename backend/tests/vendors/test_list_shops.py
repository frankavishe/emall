import pytest

from apps.accounts.models import User
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_list_shops_returns_only_own_shops(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    other_vendor = UserFactory(role=User.Role.VENDOR)
    own_shop = ShopFactory(owner=vendor, name="My Shop")
    ShopFactory(owner=other_vendor, name="Someone Else's Shop")

    _authenticate(api_client, vendor)
    response = api_client.get("/api/vendor/shops")

    assert response.status_code == 200
    names = [shop["name"] for shop in response.data]
    assert names == [own_shop.name]


def test_list_shops_forbidden_for_non_vendor(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)

    _authenticate(api_client, customer)
    response = api_client.get("/api/vendor/shops")

    assert response.status_code == 403


def test_list_shops_unauthenticated_returns_401(api_client):
    response = api_client.get("/api/vendor/shops")
    assert response.status_code == 401
