"""Business logic shared across accounts views (task T064).

Email verification and password reset use 6-digit one-time codes (OTPs) emailed to the user.
Only an HMAC of each code is stored; a code dies after use, expiry, or MAX_OTP_ATTEMPTS wrong
guesses, and issuing a new code invalidates any earlier unused one.
"""

import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.email import get_email_service

from .models import EmailVerificationToken, PasswordResetToken

VERIFICATION_TOKEN_LIFETIME = timezone.timedelta(minutes=10)
PASSWORD_RESET_TOKEN_LIFETIME = timezone.timedelta(minutes=10)


def _generate_code():
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(user, code):
    """Keyed hash so a leaked DB row can't be brute-forced back to the code offline."""
    return hmac.new(
        settings.SECRET_KEY.encode(), f"{user.pk}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def _issue_code(token_model, user, lifetime):
    token_model.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    code = _generate_code()
    token = token_model.objects.create(
        user=user,
        token=hash_code(user, code),
        expires_at=timezone.now() + lifetime,
    )
    return token, code


def issue_verification_token(user):
    """Invalidate the user's prior unused verification codes and issue+send a new one."""
    token, code = _issue_code(EmailVerificationToken, user, VERIFICATION_TOKEN_LIFETIME)
    get_email_service().send_verification_email(user, code)
    return token


def issue_password_reset_token(user):
    """Invalidate the user's prior unused reset codes and issue+send a new one."""
    token, code = _issue_code(PasswordResetToken, user, PASSWORD_RESET_TOKEN_LIFETIME)
    get_email_service().send_password_reset_email(user, code)
    return token


def check_otp(token_model, user, code):
    """Consume the user's current code if `code` matches it. Every attempt counts toward the limit.

    Commits in its own transaction so a failed guess is recorded even if the caller then errors.
    """
    with transaction.atomic():
        token = (
            token_model.objects.select_for_update()
            .filter(user=user, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if token is None or not token.is_valid():
            return False

        token.attempts += 1
        matched = hmac.compare_digest(token.token, hash_code(user, code))
        if matched:
            token.used_at = timezone.now()
        token.save(update_fields=["attempts", "used_at"])
        return matched
