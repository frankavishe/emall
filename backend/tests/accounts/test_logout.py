import pytest

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _login(api_client):
    UserFactory(email="ama@example.com", password="a-strong-password-1")
    response = api_client.post(
        "/api/auth/login",
        {"email": "ama@example.com", "password": "a-strong-password-1"},
        format="json",
    )
    return response.data["access"]


def test_logout_blacklists_refresh_and_clears_cookie(api_client, settings):
    access = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    logout_response = api_client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert logout_response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value == ""

    refresh_response = api_client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401


def test_logout_with_only_the_refresh_cookie_still_ends_the_session(api_client, settings):
    _login(api_client)  # cookie set, no Authorization header

    logout_response = api_client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert logout_response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value == ""

    assert api_client.post("/api/auth/refresh").status_code == 401


def test_logout_without_a_session_is_a_harmless_no_op(api_client):
    response = api_client.post("/api/auth/logout")
    assert response.status_code == 204
