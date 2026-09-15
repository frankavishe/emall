"""Outbound email as a swappable service interface (Constitution Principle IV).

Business logic (registration, verification, password reset) calls `EmailService` methods and
never constructs/sends email inline. The transport is Django's own mail machinery, which already
dispatches through whatever `EMAIL_BACKEND` is configured (console for local dev, SMTP/SES/etc.
in later environments) — swapping transports is purely an environment variable change, with zero
changes to `accounts` view/service code.
"""

from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail


class EmailService(ABC):
    @abstractmethod
    def send_verification_email(self, user, token):
        ...

    @abstractmethod
    def send_password_reset_email(self, user, token):
        ...


class DjangoEmailService(EmailService):
    """Sends via `django.core.mail`, transport controlled by `settings.EMAIL_BACKEND`."""

    def send_verification_email(self, user, token):
        link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
        send_mail(
            subject="Verify your email address",
            message=f"Hi {user.name},\n\nVerify your email by visiting:\n{link}\n",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    def send_password_reset_email(self, user, token):
        link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
        send_mail(
            subject="Reset your password",
            message=f"Hi {user.name},\n\nReset your password by visiting:\n{link}\n",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )


def get_email_service() -> EmailService:
    return DjangoEmailService()
