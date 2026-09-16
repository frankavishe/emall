"""Business logic shared across accounts views (task T064)."""

import secrets

from django.utils import timezone

from apps.core.email import get_email_service

from .models import EmailVerificationToken, PasswordResetToken

VERIFICATION_TOKEN_LIFETIME = timezone.timedelta(hours=24)
PASSWORD_RESET_TOKEN_LIFETIME = timezone.timedelta(hours=1)


def issue_verification_token(user):
    """Invalidate the user's prior unused verification tokens and issue+send a new one."""
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    token = EmailVerificationToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + VERIFICATION_TOKEN_LIFETIME,
    )
    get_email_service().send_verification_email(user, token.token)
    return token


def issue_password_reset_token(user):
    """Invalidate the user's prior unused reset tokens and issue+send a new one."""
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    token = PasswordResetToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + PASSWORD_RESET_TOKEN_LIFETIME,
    )
    get_email_service().send_password_reset_email(user, token.token)
    return token
