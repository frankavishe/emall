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


def test_admin_reject_pending_shop_with_reason_returns_200(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, admin)
    response = api_client.post(
        f"/api/admin/shops/{shop.id}/reject",
        {"reason": "Business documents did not match."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "REJECTED"
    assert response.data["status_reason"] == "Business documents did not match."
    shop.refresh_from_db()
    assert shop.status == Shop.Status.REJECTED
    assert shop.status_reason == "Business documents did not match."
    assert shop.status_changed_at is not None


def test_admin_reject_pending_shop_without_reason_returns_200(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, admin)
    response = api_client.post(f"/api/admin/shops/{shop.id}/reject")

    assert response.status_code == 200
    assert response.data["status"] == "REJECTED"
    shop.refresh_from_db()
    assert shop.status == Shop.Status.REJECTED


def test_admin_reject_reason_visible_to_owning_vendor(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.PENDING)

    _authenticate(api_client, admin)
    api_client.post(
        f"/api/admin/shops/{shop.id}/reject",
        {"reason": "Missing tax ID."},
        format="json",
    )

    _authenticate(api_client, vendor)
    response = api_client.get("/api/vendor/shops")

    assert response.status_code == 200
    own_shop = next(item for item in response.data if item["id"] == shop.id)
    assert own_shop["status"] == "REJECTED"
    assert own_shop["status_reason"] == "Missing tax ID."


def test_admin_reject_non_pending_shop_rejected(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(status=Shop.Status.APPROVED)

    _authenticate(api_client, admin)
    response = api_client.post(f"/api/admin/shops/{shop.id}/reject")

    assert response.status_code in (400, 409)
    shop.refresh_from_db()
    assert shop.status == Shop.Status.APPROVED


def test_admin_reject_forbidden_for_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, vendor)
    response = api_client.post(f"/api/admin/shops/{shop.id}/reject")

    assert response.status_code == 403
    shop.refresh_from_db()
    assert shop.status == Shop.Status.PENDING


def test_admin_reject_unauthenticated_returns_401(api_client):
    shop = ShopFactory(status=Shop.Status.PENDING)

    response = api_client.post(f"/api/admin/shops/{shop.id}/reject")

    assert response.status_code == 401
