import pytest
from django.utils import timezone

from apps.accounts.models import EmailVerificationToken
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_verify_email_request_issues_new_token_and_invalidates_prior(api_client):
    user = UserFactory(is_email_verified=False)
    old_token = EmailVerificationToken.objects.create(
        user=user,
        token="old-token",
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )

    _authenticate(api_client, user)
    response = api_client.post("/api/auth/verify-email/request")

    assert response.status_code == 202
    old_token.refresh_from_db()
    assert old_token.used_at is not None

    new_tokens = EmailVerificationToken.objects.filter(user=user).exclude(pk=old_token.pk)
    assert new_tokens.count() == 1
    assert new_tokens.first().used_at is None


def test_verify_email_request_unauthenticated_returns_401(api_client):
    response = api_client.post("/api/auth/verify-email/request")
    assert response.status_code == 401
