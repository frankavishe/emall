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


def test_admin_approve_pending_shop_returns_200(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, admin)
    response = api_client.post(f"/api/admin/shops/{shop.id}/approve")

    assert response.status_code == 200
    assert response.data["status"] == "APPROVED"
    shop.refresh_from_db()
    assert shop.status == Shop.Status.APPROVED
    assert shop.status_changed_at is not None


def test_admin_approve_non_pending_shop_rejected(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(status=Shop.Status.APPROVED)

    _authenticate(api_client, admin)
    response = api_client.post(f"/api/admin/shops/{shop.id}/approve")

    assert response.status_code in (400, 409)
    shop.refresh_from_db()
    assert shop.status == Shop.Status.APPROVED


def test_admin_approve_forbidden_for_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, vendor)
    response = api_client.post(f"/api/admin/shops/{shop.id}/approve")

    assert response.status_code == 403
    shop.refresh_from_db()
    assert shop.status == Shop.Status.PENDING


def test_admin_approve_unauthenticated_returns_401(api_client):
    shop = ShopFactory(status=Shop.Status.PENDING)

    response = api_client.post(f"/api/admin/shops/{shop.id}/approve")

    assert response.status_code == 401
