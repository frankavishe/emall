import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_create_shop_adds_additional_pending_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    ShopFactory(owner=vendor, name="First Shop")

    _authenticate(api_client, vendor)
    response = api_client.post("/api/vendor/shops", {"name": "Second Shop"}, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "Second Shop"
    assert response.data["status"] == "PENDING"
    assert Shop.objects.filter(owner=vendor).count() == 2
    assert Shop.objects.filter(
        owner=vendor, name="Second Shop", status=Shop.Status.PENDING
    ).exists()


def test_create_shop_rejects_duplicate_name(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    ShopFactory(name="Taken Name")

    _authenticate(api_client, vendor)
    response = api_client.post("/api/vendor/shops", {"name": "Taken Name"}, format="json")

    assert response.status_code == 400
    assert Shop.objects.filter(owner=vendor).count() == 0
