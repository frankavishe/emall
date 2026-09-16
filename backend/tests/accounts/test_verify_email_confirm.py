import pytest
from django.utils import timezone

from apps.accounts.models import EmailVerificationToken
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_verify_email_confirm_valid_token_verifies_account(api_client):
    user = UserFactory(is_email_verified=False)
    token = EmailVerificationToken.objects.create(
        user=user,
        token="valid-token",
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )

    response = api_client.post(
        "/api/auth/verify-email/confirm", {"token": token.token}, format="json"
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_email_verified is True
    token.refresh_from_db()
    assert token.used_at is not None


def test_verify_email_confirm_expired_token_returns_400(api_client):
    user = UserFactory(is_email_verified=False)
    token = EmailVerificationToken.objects.create(
        user=user,
        token="expired-token",
        expires_at=timezone.now() - timezone.timedelta(hours=1),
    )

    response = api_client.post(
        "/api/auth/verify-email/confirm", {"token": token.token}, format="json"
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_email_verified is False


def test_verify_email_confirm_used_token_returns_400(api_client):
    user = UserFactory(is_email_verified=False)
    token = EmailVerificationToken.objects.create(
        user=user,
        token="used-token",
        expires_at=timezone.now() + timezone.timedelta(hours=24),
        used_at=timezone.now(),
    )

    response = api_client.post(
        "/api/auth/verify-email/confirm", {"token": token.token}, format="json"
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_email_verified is False


def test_verify_email_confirm_unknown_token_returns_400(api_client):
    response = api_client.post(
        "/api/auth/verify-email/confirm", {"token": "does-not-exist"}, format="json"
    )

    assert response.status_code == 400


def test_verify_email_confirm_already_verified_account_returns_ok(api_client):
    user = UserFactory(is_email_verified=True)
    token = EmailVerificationToken.objects.create(
        user=user,
        token="already-verified-token",
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )

    response = api_client.post(
        "/api/auth/verify-email/confirm", {"token": token.token}, format="json"
    )

    assert response.status_code == 200
    assert "already" in response.data["detail"].lower()
