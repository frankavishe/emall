import pytest

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _login(api_client):
    UserFactory(email="ama@example.com", password="a-strong-password-1")
    return api_client.post(
        "/api/auth/login",
        {"email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )


def test_refresh_with_valid_cookie_issues_new_access(api_client):
    _login(api_client)

    response = api_client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert "access" in response.data


def test_refresh_without_cookie_fails(api_client):
    response = api_client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_refresh_with_blacklisted_cookie_fails(api_client, settings):
    login_response = _login(api_client)
    original_refresh_cookie = login_response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value

    first_refresh = api_client.post("/api/auth/refresh")
    assert first_refresh.status_code == 200

    # Reuse the original (now rotated-out, blacklisted) refresh cookie value.
    api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = original_refresh_cookie
    second_refresh = api_client.post("/api/auth/refresh")

    assert second_refresh.status_code == 401
