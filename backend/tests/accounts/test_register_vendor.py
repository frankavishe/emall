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
    assert response.data["user"]["roles"] == ["CUSTOMER", "VENDOR"]
    assert response.data["user"]["email"] == "kofi@example.com"
    assert len(response.data["shops"]) == 1
    assert response.data["shops"][0]["name"] == "Kofi's Electronics"
    assert response.data["shops"][0]["status"] == "PENDING"
    assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies

    user = User.objects.get(email="kofi@example.com")
    assert user.is_vendor
    assert Shop.objects.filter(
        owner=user, name="Kofi's Electronics", status=Shop.Status.PENDING
    ).exists()


def test_register_vendor_existing_vendor_email_rejected(api_client):
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


def test_register_vendor_with_existing_customer_email_adds_shop_to_same_account(api_client):
    customer = UserFactory(email="ama@example.com", role=User.Role.CUSTOMER)

    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Ama Owusu",
            "email": "ama@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Ama's Fabrics",
        },
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert response.data["user"]["id"] == customer.id
    assert response.data["user"]["roles"] == ["CUSTOMER", "VENDOR"]
    assert User.objects.filter(email="ama@example.com").count() == 1
    customer.refresh_from_db()
    assert customer.is_vendor
    assert Shop.objects.filter(
        owner=customer, name="Ama's Fabrics", status=Shop.Status.PENDING
    ).exists()


def test_register_vendor_with_existing_customer_email_wrong_password(api_client):
    customer = UserFactory(email="ama@example.com", role=User.Role.CUSTOMER)

    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Mallory",
            "email": "ama@example.com",
            "password": "not-amas-password-9",
            "shop_name": "Hijacked Shop",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.data
    customer.refresh_from_db()
    assert not customer.is_vendor
    assert not Shop.objects.filter(name="Hijacked Shop").exists()


def test_register_vendor_with_administrator_email_rejected(api_client):
    UserFactory(email="admin@example.com", role=User.Role.ADMINISTRATOR)

    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Admin",
            "email": "admin@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Admin Shop",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not Shop.objects.filter(name="Admin Shop").exists()
