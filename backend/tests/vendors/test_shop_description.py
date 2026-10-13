import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from apps.vendors.serializers import MAX_SHOP_DESCRIPTION_LENGTH
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _vendor_with_shop(api_client, status=Shop.Status.PENDING):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=status)
    _authenticate(api_client, vendor)
    return vendor, shop


def _patch_description(api_client, shop, data):
    return api_client.patch(f"/api/vendor/shops/{shop.id}/description", data, format="json")


def test_owner_sets_description_trimmed_and_me_includes_it(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_description(
        api_client, shop, {"description": "  Handwoven baskets.\nVisit us!  "}
    )

    assert response.status_code == 200
    assert response.data["description"] == "Handwoven baskets.\nVisit us!"
    assert response.data["status"] == "PENDING"
    me = api_client.get("/api/auth/me")
    assert me.data["shops"][0]["description"] == "Handwoven baskets.\nVisit us!"


def test_clear_description(api_client):
    _, shop = _vendor_with_shop(api_client)
    _patch_description(api_client, shop, {"description": "Something"})

    response = _patch_description(api_client, shop, {"description": ""})

    assert response.status_code == 200
    shop.refresh_from_db()
    assert shop.description == ""


def test_too_long_description_rejected(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_description(
        api_client, shop, {"description": "x" * (MAX_SHOP_DESCRIPTION_LENGTH + 1)}
    )

    assert response.status_code == 400
    assert "description" in response.data


def test_works_for_approved_shop_without_reapproval(api_client):
    _, shop = _vendor_with_shop(api_client, status=Shop.Status.APPROVED)

    response = _patch_description(api_client, shop, {"description": "Fresh produce"})

    assert response.status_code == 200
    assert response.data["status"] == "APPROVED"


def test_non_owner_gets_404(api_client):
    shop = ShopFactory()
    _authenticate(api_client, UserFactory(role=User.Role.VENDOR))

    response = _patch_description(api_client, shop, {"description": "Mine now"})

    assert response.status_code == 404


def test_anonymous_gets_401(api_client):
    shop = ShopFactory()

    response = _patch_description(api_client, shop, {"description": "Hello"})

    assert response.status_code == 401


def test_shop_create_ignores_description(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/shops", {"name": "Wordy", "description": "Ignored"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["description"] == ""
