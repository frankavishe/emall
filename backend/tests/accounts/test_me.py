import pytest

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_me_authenticated_returns_own_profile(api_client):
    UserFactory(email="ama@example.com", password="a-strong-password-1", name="Ama Owusu")
    login_response = api_client.post(
        "/api/auth/login",
        {"email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    response = api_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.data["name"] == "Ama Owusu"
    assert response.data["email"] == "ama@example.com"
    assert response.data["role"] == "CUSTOMER"
    assert response.data["is_email_verified"] is False


def test_me_unauthenticated_returns_401(api_client):
    response = api_client.get("/api/auth/me")
    assert response.status_code == 401
