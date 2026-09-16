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


def test_admin_list_shops_returns_paginated_results(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    for _ in range(3):
        ShopFactory(status=Shop.Status.PENDING)

    _authenticate(api_client, admin)
    response = api_client.get("/api/admin/shops")

    assert response.status_code == 200
    assert set(response.data.keys()) >= {"count", "next", "previous", "results"}
    assert response.data["count"] == 3
    shop = response.data["results"][0]
    assert {"id", "name", "status", "status_reason", "created_at"} <= set(shop.keys())
    assert "owner" in shop or {"owner_name", "owner_email"} <= set(shop.keys())


def test_admin_list_shops_filterable_by_status(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    pending_shop = ShopFactory(status=Shop.Status.PENDING)
    ShopFactory(status=Shop.Status.APPROVED)
    ShopFactory(status=Shop.Status.REJECTED)

    _authenticate(api_client, admin)
    response = api_client.get("/api/admin/shops", {"status": "PENDING"})

    assert response.status_code == 200
    names = [shop["name"] for shop in response.data["results"]]
    assert names == [pending_shop.name]


def test_admin_list_shops_forbidden_for_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)

    _authenticate(api_client, vendor)
    response = api_client.get("/api/admin/shops")

    assert response.status_code == 403


def test_admin_list_shops_unauthenticated_returns_401(api_client):
    response = api_client.get("/api/admin/shops")
    assert response.status_code == 401
