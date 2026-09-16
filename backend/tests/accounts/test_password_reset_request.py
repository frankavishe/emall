import pytest

from apps.accounts.models import PasswordResetToken
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_password_reset_request_registered_email_returns_202(api_client):
    user = UserFactory(email="ama@example.com")

    response = api_client.post(
        "/api/auth/password-reset/request", {"email": "ama@example.com"}, format="json"
    )

    assert response.status_code == 202
    assert (
        response.data["detail"] == "If that email is registered, a reset link has been sent."
    )
    assert PasswordResetToken.objects.filter(user=user).exists()


def test_password_reset_request_unregistered_email_returns_identical_202(api_client):
    response = api_client.post(
        "/api/auth/password-reset/request",
        {"email": "does-not-exist@example.com"},
        format="json",
    )

    assert response.status_code == 202
    assert (
        response.data["detail"] == "If that email is registered, a reset link has been sent."
    )


def test_password_reset_request_invalidates_prior_unused_tokens(api_client):
    user = UserFactory(email="ama@example.com")
    api_client.post(
        "/api/auth/password-reset/request", {"email": "ama@example.com"}, format="json"
    )
    first_token = PasswordResetToken.objects.get(user=user)

    api_client.post(
        "/api/auth/password-reset/request", {"email": "ama@example.com"}, format="json"
    )

    first_token.refresh_from_db()
    assert first_token.used_at is not None
    assert PasswordResetToken.objects.filter(user=user, used_at__isnull=True).count() == 1


def test_password_reset_request_is_throttled_after_repeated_attempts(api_client):
    payload = {"email": "does-not-exist@example.com"}

    for _ in range(5):
        response = api_client.post("/api/auth/password-reset/request", payload, format="json")
        assert response.status_code == 202

    response = api_client.post("/api/auth/password-reset/request", payload, format="json")
    assert response.status_code == 429
