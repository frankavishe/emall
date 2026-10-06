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


def _vendor_with_shop(api_client, status=Shop.Status.PENDING):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=status)
    _authenticate(api_client, vendor)
    return vendor, shop


def _patch_theme(api_client, shop, data):
    return api_client.patch(f"/api/vendor/shops/{shop.id}/theme", data, format="json")


def test_owner_sets_colors_lowercased_and_me_includes_them(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_theme(
        api_client, shop, {"primary_color": "#AA3300", "accent_color": "#ffcc00"}
    )

    assert response.status_code == 200
    assert response.data["primary_color"] == "#aa3300"
    assert response.data["accent_color"] == "#ffcc00"
    assert response.data["status"] == "PENDING"
    me = api_client.get("/api/auth/me")
    assert me.data["shops"][0]["primary_color"] == "#aa3300"


def test_partial_update_and_reset(api_client):
    _, shop = _vendor_with_shop(api_client)
    _patch_theme(api_client, shop, {"primary_color": "#112233", "accent_color": "#445566"})

    response = _patch_theme(api_client, shop, {"primary_color": ""})

    assert response.status_code == 200
    shop.refresh_from_db()
    assert shop.primary_color == ""
    assert shop.accent_color == "#445566"


@pytest.mark.parametrize("value", ["red", "#12345", "#1234567", "123456", "#ggggggg", "#gggggg"])
def test_invalid_color_rejected(api_client, value):
    _, shop = _vendor_with_shop(api_client)

    response = _patch_theme(api_client, shop, {"primary_color": value})

    assert response.status_code == 400
    assert "primary_color" in response.data


def test_works_for_approved_shop_without_reapproval(api_client):
    _, shop = _vendor_with_shop(api_client, status=Shop.Status.APPROVED)

    response = _patch_theme(api_client, shop, {"accent_color": "#00ff00"})

    assert response.status_code == 200
    assert response.data["status"] == "APPROVED"


def test_non_owner_gets_404(api_client):
    shop = ShopFactory()
    _authenticate(api_client, UserFactory(role=User.Role.VENDOR))

    response = _patch_theme(api_client, shop, {"primary_color": "#000000"})

    assert response.status_code == 404


def test_anonymous_gets_401(api_client):
    shop = ShopFactory()

    response = _patch_theme(api_client, shop, {"primary_color": "#000000"})

    assert response.status_code == 401


def test_shop_create_ignores_colors(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/shops", {"name": "Colorful", "primary_color": "#123456"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["primary_color"] == ""
