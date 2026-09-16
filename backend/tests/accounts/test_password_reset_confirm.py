import pytest
from django.utils import timezone

from apps.accounts.models import PasswordResetToken, User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _login(api_client, user, password="a-strong-password-1"):
    return api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )


def test_password_reset_confirm_valid_token_sets_new_password_and_blacklists_sessions(
    api_client,
):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    login_response = _login(api_client, user)
    assert login_response.status_code == 200

    token = PasswordResetToken.objects.create(
        user=user,
        token="valid-reset-token",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )

    response = api_client.post(
        "/api/auth/password-reset/confirm",
        {"token": token.token, "new_password": "a-new-strong-password-2"},
        format="json",
    )

    assert response.status_code == 200
    token.refresh_from_db()
    assert token.used_at is not None

    user.refresh_from_db()
    assert user.check_password("a-new-strong-password-2")
    assert not user.check_password("a-strong-password-1")

    # The pre-reset refresh cookie (still held by api_client) must now be dead.
    refresh_response = api_client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401

    old_password_login = api_client.post(
        "/api/auth/login", {"email": user.email, "password": "a-strong-password-1"}, format="json"
    )
    assert old_password_login.status_code == 401

    new_password_login = api_client.post(
        "/api/auth/login",
        {"email": user.email, "password": "a-new-strong-password-2"},
        format="json",
    )
    assert new_password_login.status_code == 200


def test_password_reset_confirm_expired_token_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    token = PasswordResetToken.objects.create(
        user=user,
        token="expired-reset-token",
        expires_at=timezone.now() - timezone.timedelta(minutes=1),
    )

    response = api_client.post(
        "/api/auth/password-reset/confirm",
        {"token": token.token, "new_password": "a-new-strong-password-2"},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_used_token_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    token = PasswordResetToken.objects.create(
        user=user,
        token="used-reset-token",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
        used_at=timezone.now(),
    )

    response = api_client.post(
        "/api/auth/password-reset/confirm",
        {"token": token.token, "new_password": "a-new-strong-password-2"},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_unknown_token_returns_400(api_client):
    response = api_client.post(
        "/api/auth/password-reset/confirm",
        {"token": "does-not-exist", "new_password": "a-new-strong-password-2"},
        format="json",
    )

    assert response.status_code == 400


def test_password_reset_confirm_weak_password_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    token = PasswordResetToken.objects.create(
        user=user,
        token="valid-reset-token-weak",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )

    response = api_client.post(
        "/api/auth/password-reset/confirm",
        {"token": token.token, "new_password": "12345"},
        format="json",
    )

    assert response.status_code == 400
    token.refresh_from_db()
    assert token.used_at is None
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")
