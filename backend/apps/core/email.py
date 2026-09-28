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
    def send_verification_email(self, user, code):
        ...

    @abstractmethod
    def send_password_reset_email(self, user, code):
        ...

    @abstractmethod
    def send_order_item_status_email(self, order_item):
        ...


class DjangoEmailService(EmailService):
    """Sends via `django.core.mail`, transport controlled by `settings.EMAIL_BACKEND`."""

    def send_verification_email(self, user, code):
        send_mail(
            subject="Your eMall verification code",
            message=(
                f"Hi {user.name},\n\n"
                f"Your eMall email verification code is: {code}\n\n"
                "It expires in 10 minutes. If you didn't create an eMall account, you can "
                "ignore this email.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    def send_password_reset_email(self, user, code):
        send_mail(
            subject="Your eMall password reset code",
            message=(
                f"Hi {user.name},\n\n"
                f"Your eMall password reset code is: {code}\n\n"
                "It expires in 10 minutes. If you didn't ask to reset your password, you can "
                "ignore this email — your password has not changed.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    def send_order_item_status_email(self, order_item):
        customer = order_item.order.customer
        product_name = order_item.product.name
        order_id = order_item.order_id

        subjects_and_states = {
            "PROCESSING": ("Your order is being prepared", "is being prepared"),
            "SHIPPED": ("Your order has shipped", "has shipped"),
            "DELIVERED": ("Your order has been delivered", "has been delivered"),
            "CANCELLED": ("An item in your order was cancelled", "was cancelled"),
        }
        subject, state = subjects_and_states[order_item.status]

        send_mail(
            subject=subject,
            message=(
                f"Hi {customer.name},\n\n"
                f"Your order #{order_id} item \"{product_name}\" {state}.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
        )


def get_email_service() -> EmailService:
    return DjangoEmailService()
