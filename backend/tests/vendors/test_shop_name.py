import pytest

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.vendors.models import Shop
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _vendor_with_shop(api_client, status=Shop.Status.PENDING, name="Old Name"):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=status, name=name)
    _authenticate(api_client, vendor)
    return vendor, shop


def _patch_name(api_client, shop, data):
    return api_client.patch(f"/api/vendor/shops/{shop.id}/name", data, format="json")


def test_owner_renames_trimmed_and_me_includes_it(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_name(api_client, shop, {"name": "  New Name  "})

    assert response.status_code == 200
    assert response.data["name"] == "New Name"
    me = api_client.get("/api/auth/me")
    assert me.data["shops"][0]["name"] == "New Name"
    event = AuditEvent.objects.get(action=AuditAction.SHOP_PROFILE_UPDATED)
    assert event.metadata["fields"] == ["name"]


def test_works_for_approved_shop_without_reapproval(api_client):
    _, shop = _vendor_with_shop(api_client, status=Shop.Status.APPROVED)

    response = _patch_name(api_client, shop, {"name": "Renamed"})

    assert response.status_code == 200
    assert response.data["status"] == "APPROVED"


def test_name_taken_by_another_shop_rejected_ignoring_case(api_client):
    ShopFactory(name="Mama Neema Crafts")
    _, shop = _vendor_with_shop(api_client)

    response = _patch_name(api_client, shop, {"name": "mama neema crafts"})

    assert response.status_code == 400
    assert "name" in response.data
    shop.refresh_from_db()
    assert shop.name == "Old Name"


def test_keeping_own_name_is_allowed_and_not_audited(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_name(api_client, shop, {"name": "Old Name"})

    assert response.status_code == 200
    assert not AuditEvent.objects.filter(action=AuditAction.SHOP_PROFILE_UPDATED).exists()


def test_blank_name_rejected(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_name(api_client, shop, {"name": "   "})

    assert response.status_code == 400
    assert "name" in response.data


def test_non_owner_gets_404(api_client):
    shop = ShopFactory()
    _authenticate(api_client, UserFactory(role=User.Role.VENDOR))

    response = _patch_name(api_client, shop, {"name": "Mine now"})

    assert response.status_code == 404


def test_anonymous_gets_401(api_client):
    shop = ShopFactory()

    response = _patch_name(api_client, shop, {"name": "Hello"})

    assert response.status_code == 401
