import pytest

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_login_success(api_client):
    UserFactory(email="ama@example.com", password="a-strong-password-1")

    response = api_client.post(
        "/api/auth/login",
        {"email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert response.data["user"]["email"] == "ama@example.com"


def test_login_wrong_password_returns_generic_message(api_client):
    UserFactory(email="ama@example.com", password="a-strong-password-1")

    response = api_client.post(
        "/api/auth/login",
        {"email": "ama@example.com", "password": "totally-wrong"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["detail"] == "Invalid email or password."


def test_login_unregistered_email_returns_same_generic_message(api_client):
    response = api_client.post(
        "/api/auth/login",
        {"email": "nobody@example.com", "password": "totally-wrong"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["detail"] == "Invalid email or password."
