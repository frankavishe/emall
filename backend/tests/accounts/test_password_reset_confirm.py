import pytest
from django.utils import timezone

from apps.accounts.models import MAX_OTP_ATTEMPTS, PasswordResetToken
from apps.accounts.services import hash_code
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

URL = "/api/auth/password-reset/confirm"


def _login(api_client, user, password="a-strong-password-1"):
    return api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )


def _make_code(user, code="123456", **kwargs):
    kwargs.setdefault("expires_at", timezone.now() + timezone.timedelta(minutes=10))
    return PasswordResetToken.objects.create(user=user, token=hash_code(user, code), **kwargs)


def _confirm(api_client, email, code="123456", new_password="a-new-strong-password-2"):
    return api_client.post(
        URL, {"email": email, "code": code, "new_password": new_password}, format="json"
    )


def test_password_reset_confirm_valid_code_sets_new_password_and_blacklists_sessions(
    api_client,
):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    login_response = _login(api_client, user)
    assert login_response.status_code == 200

    token = _make_code(user)

    response = _confirm(api_client, user.email)

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


def test_password_reset_confirm_code_cannot_be_reused(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    _make_code(user)

    assert _confirm(api_client, user.email).status_code == 200
    response = _confirm(api_client, user.email, new_password="a-third-strong-password-3")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-new-strong-password-2")


def test_password_reset_confirm_wrong_code_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    token = _make_code(user)

    response = _confirm(api_client, user.email, code="654321")

    assert response.status_code == 400
    token.refresh_from_db()
    assert token.attempts == 1
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_locks_code_after_max_attempts(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    _make_code(user)

    for _ in range(MAX_OTP_ATTEMPTS):
        _confirm(api_client, user.email, code="000000")

    response = _confirm(api_client, user.email)

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_expired_code_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    _make_code(user, expires_at=timezone.now() - timezone.timedelta(minutes=1))

    response = _confirm(api_client, user.email)

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_used_code_returns_400(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    _make_code(user, used_at=timezone.now())

    response = _confirm(api_client, user.email)

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")


def test_password_reset_confirm_unknown_email_returns_400(api_client):
    response = _confirm(api_client, "nobody@example.com")

    assert response.status_code == 400


def test_password_reset_confirm_weak_password_returns_400_without_consuming_code(api_client):
    user = UserFactory(email="ama@example.com", password="a-strong-password-1")
    token = _make_code(user)

    response = _confirm(api_client, user.email, new_password="12345")

    assert response.status_code == 400
    token.refresh_from_db()
    assert token.used_at is None
    assert token.attempts == 0
    user.refresh_from_db()
    assert user.check_password("a-strong-password-1")
