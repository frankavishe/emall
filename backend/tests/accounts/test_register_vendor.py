import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_register_vendor_success(api_client, settings):
    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Kofi Mensah",
            "email": "kofi@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Kofi's Electronics",
        },
        format="json",
    )

    assert response.status_code == 201
    assert "access" in response.data
    assert response.data["user"]["role"] == "VENDOR"
    assert response.data["user"]["email"] == "kofi@example.com"
    assert len(response.data["shops"]) == 1
    assert response.data["shops"][0]["name"] == "Kofi's Electronics"
    assert response.data["shops"][0]["status"] == "PENDING"
    assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies

    user = User.objects.get(email="kofi@example.com")
    assert user.role == User.Role.VENDOR
    assert Shop.objects.filter(
        owner=user, name="Kofi's Electronics", status=Shop.Status.PENDING
    ).exists()


def test_register_vendor_duplicate_email(api_client):
    UserFactory(email="kofi@example.com", role=User.Role.VENDOR)

    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Kofi Mensah",
            "email": "kofi@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Kofi's Electronics",
        },
        format="json",
    )

    assert response.status_code == 400


def test_register_vendor_duplicate_shop_name(api_client):
    ShopFactory(name="Kofi's Electronics")

    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Ama Owusu",
            "email": "ama-vendor@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Kofi's Electronics",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="ama-vendor@example.com").exists()


def test_register_vendor_weak_password(api_client):
    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Kofi Mensah",
            "email": "weak-vendor@example.com",
            "password": "12345",
            "shop_name": "Weak Shop",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="weak-vendor@example.com").exists()
    assert not Shop.objects.filter(name="Weak Shop").exists()
