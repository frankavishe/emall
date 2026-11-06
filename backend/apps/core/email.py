"""Outbound email as a swappable service interface (Constitution Principle IV).

Business logic (registration, verification, password reset) calls `EmailService` methods and
never constructs/sends email inline. The transport is Django's own mail machinery, which already
dispatches through whatever `EMAIL_BACKEND` is configured (console for local dev, SMTP/SES/etc.
in later environments) — swapping transports is purely an environment variable change, with zero
changes to `accounts` view/service code.
"""

from abc import ABC, abstractmethod
from zoneinfo import ZoneInfo

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

    @abstractmethod
    def send_order_confirmation_email(self, order):
        ...

    @abstractmethod
    def send_shop_approved_email(self, shop):
        ...

    @abstractmethod
    def send_low_stock_email(self, product):
        ...

    @abstractmethod
    def send_booking_status_email(self, booking, status):
        ...


def guest_order_url(order):
    """The guest's private link back to their order (guest checkout)."""

    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/orders/track/{order.access_token}"


def _payment_line(order):
    """Cash on delivery is the only way a confirmed order can still be unpaid."""

    payment = getattr(order, "payment", None)
    if payment is not None and payment.method == "cod" and payment.status == "PENDING":
        return f"Please have TZS {order.total:,.2f} ready to pay in cash on delivery."
    return "Payment received - thank you."


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
        order = order_item.order
        product_name = order_item.product.name
        order_id = order_item.order_id

        subjects_and_states = {
            "PROCESSING": ("Your order is being prepared", "is being prepared"),
            "SHIPPED": ("Your order has shipped", "has shipped"),
            "DELIVERED": ("Your order has been delivered", "has been delivered"),
            "CANCELLED": ("An item in your order was cancelled", "was cancelled"),
        }
        subject, state = subjects_and_states[order_item.status]

        message = (
            f"Hi {order.contact_name},\n\n"
            f"Your order #{order_id} item \"{product_name}\" {state}.\n"
        )
        if order.is_guest:
            message += f"\nTrack your order: {guest_order_url(order)}\n"
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.contact_email],
        )

    def send_order_confirmation_email(self, order):
        lines = "\n".join(
            f"  - {item.product.name} x{item.quantity}"
            for item in order.items.select_related("product")
        )
        send_mail(
            subject=f"Your eMall order #{order.id} is confirmed",
            message=(
                f"Hi {order.contact_name},\n\n"
                f"Thanks for your order #{order.id}.\n\n"
                f"{lines}\n\n"
                f"Total: TZS {order.total:,.2f}\n"
                f"{_payment_line(order)}\n\n"
                "Follow your order at any time with this private link (keep it to yourself: "
                "anyone with it can see the order):\n"
                f"{guest_order_url(order)}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.contact_email],
        )

    def send_shop_approved_email(self, shop):
        owner = shop.owner
        send_mail(
            subject=f'Your eMall shop "{shop.name}" is approved',
            message=(
                f"Hi {owner.name},\n\n"
                f'Good news - your shop "{shop.name}" has been approved and is now live on '
                "eMall. Customers can find it and buy your published products.\n\n"
                f"Manage your shop: {settings.FRONTEND_BASE_URL.rstrip('/')}/vendor/products\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
        )

    def send_low_stock_email(self, product):
        owner = product.shop.owner
        remaining = product.stock_quantity or 0
        if remaining:
            subject = f'Low stock: "{product.name}"'
            status = f"is running low - only {remaining} left"
        else:
            subject = f'Out of stock: "{product.name}"'
            status = "has sold out and is no longer available to customers"
        send_mail(
            subject=subject,
            message=(
                f"Hi {owner.name},\n\n"
                f'Your product "{product.name}" {status}.\n\n'
                "Restock it here: "
                f"{settings.FRONTEND_BASE_URL.rstrip('/')}/vendor/products/{product.id}/edit\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
        )

    def send_booking_status_email(self, booking, status):
        """`status` is the one the booking just moved to; see `_booking_email` for who hears."""

        email = _booking_email(booking, status)
        if email is None:
            return
        user, path, subject, body = email
        send_mail(
            subject=subject,
            message=(
                f"Hi {user.name},\n\n"
                f"{body}\n\n"
                f"View it here: {settings.FRONTEND_BASE_URL.rstrip('/')}{path}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )


def _market_time(value):
    local = value.astimezone(ZoneInfo(settings.MARKET_TIME_ZONE))
    return f"{local:%a %d %b %Y at %H:%M} (Dar es Salaam time)"


def _booking_email(booking, status):
    """Who hears about a status change and what they read (FR-032), as `(recipient, link path,
    subject, body)`. None for a status that notifies nobody."""

    service = booking.service.name
    when = _market_time(booking.starts_at)
    customer_path = f"/bookings/{booking.id}"
    reason = f"\n\nReason: {booking.status_reason}" if booking.status_reason else ""

    if status == "REQUESTED":
        return (
            booking.shop.owner,
            "/vendor/bookings",
            f'New booking request: "{service}"',
            f'{booking.customer.name} asked to book "{service}" on {when}. Please accept or '
            f"decline by {_market_time(booking.respond_by)}.",
        )
    if status == "AWAITING_PAYMENT":
        return (
            booking.customer,
            customer_path,
            f'Your booking for "{service}" was accepted',
            f"{booking.shop.name} accepted your booking on {when}. Please pay by "
            f"{_market_time(booking.pay_by)} to confirm it.",
        )
    if status == "DECLINED":
        return (
            booking.customer,
            customer_path,
            f'Your booking for "{service}" was declined',
            f"{booking.shop.name} can't take your booking on {when}, and you haven't been "
            f"charged.{reason}",
        )
    if status == "EXPIRED":
        return (
            booking.customer,
            customer_path,
            f'Your booking for "{service}" expired',
            f"Your booking on {when} expired before it was confirmed, and you haven't been "
            "charged. You're welcome to book another time.",
        )
    if status == "CANCELLED":
        return (
            booking.shop.owner,
            "/vendor/bookings",
            f'A booking for "{service}" was cancelled',
            f"{booking.customer.name} cancelled their booking on {when}, so the time is open "
            "again.",
        )
    return None


def get_email_service() -> EmailService:
    return DjangoEmailService()
