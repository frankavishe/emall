import pytest
from django.utils import timezone

from apps.accounts.models import MAX_OTP_ATTEMPTS, EmailVerificationToken
from apps.accounts.services import hash_code
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

URL = "/api/auth/verify-email/confirm"


def _make_code(user, code="123456", **kwargs):
    kwargs.setdefault("expires_at", timezone.now() + timezone.timedelta(minutes=10))
    return EmailVerificationToken.objects.create(
        user=user, token=hash_code(user, code), **kwargs
    )


def test_verify_email_confirm_valid_code_verifies_account(api_client):
    user = UserFactory(is_email_verified=False)
    token = _make_code(user)

    response = api_client.post(URL, {"email": user.email, "code": "123456"}, format="json")

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_email_verified is True
    token.refresh_from_db()
    assert token.used_at is not None


def test_verify_email_confirm_email_is_case_insensitive(api_client):
    user = UserFactory(email="ama@example.com", is_email_verified=False)
    _make_code(user)

    response = api_client.post(
        URL, {"email": "AMA@Example.com", "code": "123456"}, format="json"
    )

    assert response.status_code == 200


def test_verify_email_confirm_wrong_code_returns_400_and_counts_attempt(api_client):
    user = UserFactory(is_email_verified=False)
    token = _make_code(user)

    response = api_client.post(URL, {"email": user.email, "code": "654321"}, format="json")

    assert response.status_code == 400
    token.refresh_from_db()
    assert token.attempts == 1
    assert token.used_at is None
    user.refresh_from_db()
    assert user.is_email_verified is False


def test_verify_email_confirm_locks_code_after_max_attempts(api_client):
    user = UserFactory(is_email_verified=False)
    _make_code(user)

    for _ in range(MAX_OTP_ATTEMPTS):
        api_client.post(URL, {"email": user.email, "code": "000000"}, format="json")

    response = api_client.post(URL, {"email": user.email, "code": "123456"}, format="json")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_email_verified is False


def test_verify_email_confirm_expired_code_returns_400(api_client):
    user = UserFactory(is_email_verified=False)
    _make_code(user, expires_at=timezone.now() - timezone.timedelta(minutes=1))

    response = api_client.post(URL, {"email": user.email, "code": "123456"}, format="json")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_email_verified is False


def test_verify_email_confirm_used_code_returns_400(api_client):
    user = UserFactory(is_email_verified=False)
    _make_code(user, used_at=timezone.now())

    response = api_client.post(URL, {"email": user.email, "code": "123456"}, format="json")

    assert response.status_code == 400


def test_verify_email_confirm_other_users_code_returns_400(api_client):
    owner = UserFactory(is_email_verified=False)
    other = UserFactory(is_email_verified=False)
    _make_code(owner)

    response = api_client.post(URL, {"email": other.email, "code": "123456"}, format="json")

    assert response.status_code == 400
    other.refresh_from_db()
    assert other.is_email_verified is False


def test_verify_email_confirm_unknown_email_returns_400(api_client):
    response = api_client.post(
        URL, {"email": "nobody@example.com", "code": "123456"}, format="json"
    )

    assert response.status_code == 400


def test_verify_email_confirm_malformed_code_returns_400(api_client):
    user = UserFactory(is_email_verified=False)

    response = api_client.post(URL, {"email": user.email, "code": "12ab"}, format="json")

    assert response.status_code == 400


def test_verify_email_confirm_already_verified_account_returns_ok(api_client):
    user = UserFactory(is_email_verified=True)

    response = api_client.post(URL, {"email": user.email, "code": "123456"}, format="json")

    assert response.status_code == 200
    assert "already" in response.data["detail"].lower()
