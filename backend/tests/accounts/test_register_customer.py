import pytest

from apps.accounts.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_register_customer_success(api_client, settings):
    response = api_client.post(
        "/api/auth/register/customer",
        {"name": "Ama Owusu", "email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )

    assert response.status_code == 201
    assert "access" in response.data
    assert response.data["user"]["role"] == "CUSTOMER"
    assert response.data["user"]["email"] == "ama@example.com"
    assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies
    assert User.objects.filter(email="ama@example.com", role=User.Role.CUSTOMER).exists()


def test_register_customer_duplicate_email(api_client):
    UserFactory(email="ama@example.com")

    response = api_client.post(
        "/api/auth/register/customer",
        {"name": "Ama Owusu", "email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )

    assert response.status_code == 400


def test_register_customer_case_insensitive_duplicate_email(api_client):
    UserFactory(email="user@x.com")

    response = api_client.post(
        "/api/auth/register/customer",
        {"name": "Someone Else", "email": "User@x.com", "password": "a-strong-password-1"},
        format="json",
    )

    assert response.status_code == 400


def test_register_customer_weak_password(api_client):
    response = api_client.post(
        "/api/auth/register/customer",
        {"name": "Ama Owusu", "email": "weak@example.com", "password": "12345"},
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="weak@example.com").exists()
