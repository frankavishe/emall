"""Every booking status change. Each one runs in a transaction with the booking row locked, so if
an accept, a cancel and a deadline land together only one takes effect, and the others see the
current status."""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.exceptions import APIException, PermissionDenied

from apps.audit.models import AuditAction
from apps.audit.services import record
from apps.bookings.models import Booking, BookingStatusEvent, Service
from apps.bookings.permissions import require_bookable_shop
from apps.bookings.slots import market_zone, open_slots
from apps.core.email import get_email_service
from apps.finance.services import split_line
from apps.realtime.broadcast import publish_on_commit
from apps.realtime.groups import ADMINS, booking_audience, user_group
from apps.vendors.models import Shop

logger = logging.getLogger(__name__)

TIME_UNAVAILABLE = "This time is no longer available. Please choose another."
SERVICE_NOT_FOUND = "This service isn't available right now."


class BookingRefused(APIException):
    status_code = http_status.HTTP_400_BAD_REQUEST
    default_code = "booking_refused"


class BookingConflict(APIException):
    """The action doesn't fit the booking's current status."""

    status_code = http_status.HTTP_409_CONFLICT
    default_code = "booking_conflict"


def _send_status_email(booking, status):
    """Best-effort: the status change is already committed (FR-032)."""

    try:
        get_email_service().send_booking_status_email(booking, status)
    except Exception:
        logger.exception("Failed to send booking email for booking_id=%s", booking.id)


def _record_status(booking, status, *, action, actor, request, reason=""):
    """The history row, audit entry, live hint and email that every status change produces."""

    BookingStatusEvent.objects.create(booking=booking, status=status, actor=actor, reason=reason)
    record(action, request=request, target=booking, metadata={"status": status})
    transaction.on_commit(lambda: _send_status_email(booking, status))


def _announce_update(booking):
    publish_on_commit(
        booking_audience(booking), {"type": "booking.updated", "booking_id": booking.id}
    )


def _change_status(booking, status, *, action, actor=None, request=None, reason="", **fields):
    booking.status = status
    booking.status_reason = reason
    for name, value in fields.items():
        setattr(booking, name, value)
    booking.save(update_fields=["status", "status_reason", *fields])
    _record_status(booking, status, action=action, actor=actor, request=request, reason=reason)
    _announce_update(booking)


def _locked(queryset, booking_id):
    """The booking with its row locked, or a 404. `of` keeps the lock off any table a filter
    joined, and `no_key` doesn't block rows that only reference the booking."""

    booking = queryset.select_for_update(no_key=True, of=("self",)).filter(pk=booking_id).first()
    if booking is None:
        raise Http404
    return booking


def _lock_guest_email(email):
    """Serialises one guest email's requests across shops for the unpaid limit, the way the
    user row lock does for a signed-in customer. Released when the transaction ends."""

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))", [f"booking-guest:{email.lower()}"]
        )


def request_booking(
    *,
    customer=None,
    guest_name="",
    guest_email="",
    service_id,
    starts_at,
    contact_phone,
    customer_note="",
    request=None,
    now=None,
):
    """Holds a time for `customer`, or for a guest identified by `guest_email` when there is no
    customer. Locking the shop serialises requests for its capacity, and locking the customer
    (or guest email) serialises their requests across shops for the unpaid limit. Always in that
    order, so two requests can't deadlock."""

    if customer is None and not guest_email:
        raise ValueError("A booking needs a customer or a guest email.")

    now = now or timezone.now()
    shop_id = (
        Service.objects.visible().filter(pk=service_id).values_list("shop_id", flat=True).first()
    )
    if shop_id is None:
        raise Http404(SERVICE_NOT_FOUND)

    with transaction.atomic():
        if customer is not None:
            get_user_model().objects.select_for_update(no_key=True).get(pk=customer.pk)
        else:
            _lock_guest_email(guest_email)
        shop = Shop.objects.select_for_update(no_key=True).get(pk=shop_id)
        # Read again under the lock: the shop or service may have changed in the meantime.
        service = Service.objects.visible().filter(pk=service_id).first()
        if service is None:
            raise Http404(SERVICE_NOT_FOUND)
        service.shop = shop

        if customer is not None and shop.owner_id == customer.pk:
            raise PermissionDenied("You can't book a service from your own shop.")

        mine = (
            {"customer": customer}
            if customer is not None
            else {"customer__isnull": True, "guest_email__iexact": guest_email}
        )
        unpaid = Booking.objects.active_unpaid(now).filter(**mine).count()
        if unpaid >= settings.BOOKING_MAX_ACTIVE_UNPAID:
            raise BookingRefused(
                f"You already have {settings.BOOKING_MAX_ACTIVE_UNPAID} bookings waiting on a "
                "response or payment. Finish or cancel one first."
            )

        local_date = starts_at.astimezone(market_zone()).date()
        slot = next(
            (s for s in open_slots(service, local_date, now=now) if s.starts_at == starts_at),
            None,
        )
        if slot is None:
            raise BookingRefused(TIME_UNAVAILABLE)

        rate = shop.effective_commission_rate()
        commission_amount, vendor_earning = split_line(service.price, rate)
        booking = Booking.objects.create(
            customer=customer,
            guest_name="" if customer is not None else guest_name,
            guest_email="" if customer is not None else guest_email,
            access_token=None if customer is not None else secrets.token_urlsafe(32),
            shop=shop,
            service=service,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            respond_by=min(
                now + timedelta(hours=settings.BOOKING_RESPONSE_HOURS),
                slot.starts_at - timedelta(minutes=settings.BOOKING_RESPONSE_BUFFER_MINUTES),
            ),
            contact_phone=contact_phone,
            customer_note=customer_note,
            price=service.price,
            commission_rate=rate,
            commission_amount=commission_amount,
            vendor_earning=vendor_earning,
        )
        _record_status(
            booking,
            Booking.Status.REQUESTED,
            action=AuditAction.BOOKING_REQUESTED,
            actor=customer,
            request=request,
        )
        publish_on_commit(
            [user_group(shop.owner_id), ADMINS],
            {"type": "booking.created", "booking_id": booking.id},
        )
    return booking


def expire_due_bookings(queryset=None, *, now=None):
    """Ends bookings past their deadline and returns how many it changed. Safe to run at any time:
    each row is rechecked under its lock, and one being changed by someone else is left for the
    next pass. The time itself freed up when the deadline passed (`holding`)."""

    now = now or timezone.now()
    queryset = Booking.objects.all() if queryset is None else queryset
    due_ids = list(queryset.due_for_expiry(now).order_by().values_list("pk", flat=True))

    changed = 0
    for booking_id in due_ids:
        with transaction.atomic():
            booking = (
                Booking.objects.due_for_expiry(now)
                .select_for_update(no_key=True, skip_locked=True)
                .filter(pk=booking_id)
                .first()
            )
            if booking is None:
                continue
            _change_status(booking, Booking.Status.EXPIRED, action=AuditAction.BOOKING_EXPIRED)
            changed += 1
    return changed


def _lock_request_for_answer(*, booking_id, owner, now):
    """The provider's own booking, still waiting and still inside its deadline."""

    booking = _locked(Booking.objects.filter(shop__owner=owner), booking_id)
    require_bookable_shop(booking.shop)
    if booking.status != Booking.Status.REQUESTED or booking.respond_by <= now:
        raise BookingConflict(f"This booking can't be answered: it is {_status_label(booking)}.")
    return booking


def _status_label(booking):
    return booking.get_status_display().lower()


def accept_booking(*, booking_id, owner, request=None, now=None):
    now = now or timezone.now()
    # In its own transaction, so a late accept still records the expiry before it's refused.
    expire_due_bookings(Booking.objects.filter(pk=booking_id, shop__owner=owner), now=now)

    with transaction.atomic():
        booking = _lock_request_for_answer(booking_id=booking_id, owner=owner, now=now)
        _change_status(
            booking,
            Booking.Status.AWAITING_PAYMENT,
            action=AuditAction.BOOKING_ACCEPTED,
            actor=owner,
            request=request,
            accepted_at=now,
            pay_by=min(
                now + timedelta(hours=settings.BOOKING_PAYMENT_HOURS),
                booking.starts_at - timedelta(minutes=settings.BOOKING_PAYMENT_BUFFER_MINUTES),
            ),
        )
    return booking


def decline_booking(*, booking_id, owner, reason="", request=None, now=None):
    now = now or timezone.now()
    expire_due_bookings(Booking.objects.filter(pk=booking_id, shop__owner=owner), now=now)

    with transaction.atomic():
        booking = _lock_request_for_answer(booking_id=booking_id, owner=owner, now=now)
        _change_status(
            booking,
            Booking.Status.DECLINED,
            action=AuditAction.BOOKING_DECLINED,
            actor=owner,
            request=request,
            reason=reason,
        )
    return booking


def cancel_unpaid_booking(*, booking_id, customer=None, access_token=None, request=None, now=None):
    """The customer ending their own request or accepted booking, at no charge. A guest is
    identified by the booking's `access_token` instead of a customer."""

    now = now or timezone.now()
    if customer is not None:
        mine = Booking.objects.filter(customer=customer)
    elif access_token:
        mine = Booking.objects.filter(customer__isnull=True, access_token=access_token)
    else:
        raise Http404
    expire_due_bookings(mine.filter(pk=booking_id), now=now)

    with transaction.atomic():
        booking = _locked(mine, booking_id)
        if not Booking.objects.active_unpaid(now).filter(pk=booking.pk).exists():
            raise BookingConflict(
                f"This booking can't be cancelled: it is {_status_label(booking)}."
            )
        _change_status(
            booking,
            Booking.Status.CANCELLED,
            action=AuditAction.BOOKING_CANCELLED,
            actor=customer,
            request=request,
            cancelled_at=now,
        )
    return booking
