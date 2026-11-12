"""Every booking status change. Each one runs in a transaction with the booking row locked, so if
an accept, a cancel and a deadline land together only one takes effect, and the others see the
current status."""

import logging
import secrets
import uuid
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
from apps.payments.models import PaymentRecord, RefundDue
from apps.payments.outcomes import complete_payment, expire_stale_payments
from apps.payments.services import (
    LIPA_NAMBA_METHOD,
    MOBILE_MONEY_METHOD,
    InitiationResult,
    available_payment_methods,
    get_mobile_money_gateway,
)
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


# --- Payment -------------------------------------------------------------------

PAYMENT_IN_PROGRESS = (
    "A payment for this booking is still being processed. Please wait until it finishes."
)


def _customer_bookings(customer=None, access_token=None):
    """A signed-in customer's bookings, or the one guest booking its `access_token` opens."""

    if customer is not None:
        return Booking.objects.filter(customer=customer)
    if access_token:
        return Booking.objects.filter(customer__isnull=True, access_token=access_token)
    raise Http404


def settle_stale_payments(bookings=None):
    """Fails booking mobile-money payments that have timed out (never Lipa Namba: an
    administrator settles those). Returns how many it failed."""

    records = PaymentRecord.objects.filter(booking__isnull=False)
    if bookings is not None:
        records = records.filter(booking__in=bookings)
    return expire_stale_payments(queryset=records)


def refresh_bookings(bookings=None, *, now=None):
    """The lazy cleanup before a read or an action: stale payments first, then deadlines, in
    the same order as the scheduled command. Returns how many bookings expired."""

    settle_stale_payments(bookings)
    return expire_due_bookings(bookings, now=now)


def _payment_in_progress(booking):
    return booking.payments.filter(status=PaymentRecord.Status.PENDING).exists()


def _paid_record(booking):
    return booking.payments.filter(status=PaymentRecord.Status.SUCCEEDED).first()


def booking_payment_methods(booking, now=None):
    """What this booking can be paid with: mobile money, and Lipa Namba while the visit is far
    enough away for an administrator to check the statement (FR-018). Never card or cash."""

    now = now or timezone.now()
    lipa_allowed = booking.starts_at - now >= timedelta(hours=settings.BOOKING_LIPA_MIN_HOURS)
    return [
        option
        for option in available_payment_methods()
        if option["method"] == MOBILE_MONEY_METHOD
        or (option["method"] == LIPA_NAMBA_METHOD and lipa_allowed)
    ]


def start_booking_payment(
    *,
    booking_id,
    payment_method,
    customer=None,
    access_token=None,
    msisdn="",
    provider="",
    payer_reference="",
    now=None,
):
    """Starts one payment attempt for an accepted booking, for `booking.amount_due()` and never
    an amount from the client. A mobile-money push is sent after commit, outside the row locks,
    as checkout does (`_place_mobile_money_order`). Returns the booking."""

    now = now or timezone.now()
    mine = _customer_bookings(customer, access_token)
    refresh_bookings(mine.filter(pk=booking_id), now=now)

    with transaction.atomic():
        booking = _locked(mine, booking_id)
        if booking.status != Booking.Status.AWAITING_PAYMENT or booking.pay_by <= now:
            raise BookingConflict(f"This booking can't be paid: it is {_status_label(booking)}.")
        if booking.payments.filter(
            status__in=[PaymentRecord.Status.PENDING, PaymentRecord.Status.SUCCEEDED]
        ).exists():
            raise BookingConflict(PAYMENT_IN_PROGRESS)
        offered = {option["method"] for option in booking_payment_methods(booking, now)}
        if payment_method not in offered:
            raise BookingRefused("This payment method isn't available for this booking.")

        fields = (
            {"provider_reference": payer_reference}
            if payment_method == LIPA_NAMBA_METHOD
            else {"provider": provider, "msisdn": msisdn}
        )
        payment = PaymentRecord.objects.create(
            booking=booking,
            method=payment_method,
            amount=booking.amount_due(),
            status=PaymentRecord.Status.PENDING,
            transaction_reference=uuid.uuid4().hex,
            **fields,
        )
        _announce_update(booking)

    if payment_method == MOBILE_MONEY_METHOD:
        _push_payment_prompt(payment)
    booking.refresh_from_db()
    return booking


def _push_payment_prompt(payment):
    try:
        result = get_mobile_money_gateway().initiate(
            amount=payment.amount,
            msisdn=payment.msisdn,
            provider=payment.provider,
            external_id=payment.transaction_reference,
        )
    except Exception:
        logger.exception("Mobile money initiation crashed for booking %s", payment.booking_id)
        result = InitiationResult(accepted=False, message="Payment provider unavailable.")

    if not result.accepted:
        complete_payment(record_id=payment.id, success=False, message=result.message)
        raise BookingRefused(result.message or "The payment request could not be sent.")
    if result.provider_reference:
        PaymentRecord.objects.filter(pk=payment.pk).update(
            provider_reference=result.provider_reference
        )


def _owe_back(payment, *, amount, reason, note="", request=None):
    """Puts money on the refund list once per payment and reason: a repeated callback or click
    finds the existing entry."""

    refund, created = RefundDue.objects.get_or_create(
        payment=payment, reason=reason, defaults={"amount": amount, "note": note}
    )
    if created:
        record(
            AuditAction.REFUND_CREATED,
            request=request,
            target=payment.booking,
            metadata={"refund_id": refund.id, "amount": refund.amount, "reason": refund.reason},
        )
        publish_on_commit([ADMINS], {"type": "refund.updated", "refund_id": refund.id})
    return refund


def _confirm_or_refund(booking, payment, *, honourable, now):
    """Every successful payment ends as a confirmed booking or a refund entry (SC-004)."""

    if honourable:
        _change_status(
            booking,
            Booking.Status.CONFIRMED,
            action=AuditAction.BOOKING_CONFIRMED,
            confirmed_at=now,
        )
        return
    _owe_back(
        payment,
        amount=payment.amount,
        reason=RefundDue.Reason.LATE_PAYMENT,
        note=f"Paid while the booking was {_status_label(booking)}.",
    )
    # A booking that can no longer be paid ends now rather than at the next sweep.
    if Booking.objects.due_for_expiry(now).filter(pk=booking.pk).exists():
        _change_status(booking, Booking.Status.EXPIRED, action=AuditAction.BOOKING_EXPIRED)


def on_payment_settled(payment, *, success, now=None):
    """Called by `complete_payment` with the payment already locked and settled; locks the
    booking second (research.md §7). A PENDING payment held the time, so a success confirms the
    booking as long as it is still waiting and the visit hasn't started. A failure leaves the
    booking as it is, free to retry until the deadline."""

    if not success:
        return
    now = now or timezone.now()
    booking = Booking.objects.select_for_update(no_key=True, of=("self",)).get(
        pk=payment.booking_id
    )
    payment.booking = booking
    honourable = booking.status == Booking.Status.AWAITING_PAYMENT and booking.starts_at > now
    _confirm_or_refund(booking, payment, honourable=honourable, now=now)


def reconcile_late_payment(*, record_id, provider_reference="", now=None):
    """A success callback for a payment we had already failed (it timed out, or the push was
    reported refused). The money is real, so it confirms the booking only if the time was still
    held, nothing else was paid and the visit hasn't started; otherwise it is owed back."""

    now = now or timezone.now()
    with transaction.atomic():
        payment = PaymentRecord.objects.select_for_update(of=("self",)).get(pk=record_id)
        if payment.status != PaymentRecord.Status.FAILED:
            return payment
        booking = Booking.objects.select_for_update(no_key=True, of=("self",)).get(
            pk=payment.booking_id
        )
        payment.booking = booking
        other_live = (
            booking.payments.exclude(pk=payment.pk)
            .filter(status__in=[PaymentRecord.Status.PENDING, PaymentRecord.Status.SUCCEEDED])
            .exists()
        )
        if provider_reference:
            payment.provider_reference = provider_reference
        if other_live:
            # Only one live payment per booking: this one stays failed, and is owed back.
            payment.failure_reason = "Paid after another payment; on the refund list."
        else:
            payment.status = PaymentRecord.Status.SUCCEEDED
            payment.failure_reason = ""
        payment.save()

        honourable = (
            not other_live
            and booking.status == Booking.Status.AWAITING_PAYMENT
            and booking.pay_by > now
            and booking.starts_at > now
        )
        _confirm_or_refund(booking, payment, honourable=honourable, now=now)
        record(
            AuditAction.PAYMENT_COMPLETED,
            target=booking,
            target_repr=f"Booking #{booking.id}",
            metadata={
                "reference": payment.transaction_reference,
                "method": payment.method,
                "amount": payment.amount,
                "late": True,
            },
        )
        _announce_update(booking)
    return payment


# --- Cancellation ----------------------------------------------------------------


def _cancel(booking, *, actor, request, now, reason=""):
    _change_status(
        booking,
        Booking.Status.CANCELLED,
        action=AuditAction.BOOKING_CANCELLED,
        actor=actor,
        request=request,
        reason=reason,
        cancelled_at=now,
    )


def _refuse_if_paying(booking):
    if _payment_in_progress(booking):
        raise BookingConflict(PAYMENT_IN_PROGRESS)


def _is_unpaid_and_active(booking, now):
    return Booking.objects.active_unpaid(now).filter(pk=booking.pk).exists()


def _cannot_cancel(booking):
    return BookingConflict(f"This booking can't be cancelled: it is {_status_label(booking)}.")


def cancel_customer_booking(
    *, booking_id, customer=None, access_token=None, request=None, now=None
):
    """The customer ending their own booking: free before payment, and for a full refund once
    paid if the visit is at least `BOOKING_CUSTOMER_CANCEL_HOURS` away (FR-024). A guest is
    identified by the booking's `access_token` instead of a customer."""

    now = now or timezone.now()
    mine = _customer_bookings(customer, access_token)
    refresh_bookings(mine.filter(pk=booking_id), now=now)

    with transaction.atomic():
        booking = _locked(mine, booking_id)
        _refuse_if_paying(booking)
        if _is_unpaid_and_active(booking, now):
            _cancel(booking, actor=customer, request=request, now=now)
            return booking
        if booking.status != Booking.Status.CONFIRMED:
            raise _cannot_cancel(booking)
        if booking.starts_at - now < timedelta(hours=settings.BOOKING_CUSTOMER_CANCEL_HOURS):
            raise BookingConflict(
                f"This booking starts in less than {settings.BOOKING_CUSTOMER_CANCEL_HOURS} "
                "hours, so it can't be cancelled here. Please contact support."
            )
        _cancel(booking, actor=customer, request=request, now=now)
        paid = _paid_record(booking)
        if paid is not None:
            _owe_back(
                paid,
                amount=paid.amount,
                reason=RefundDue.Reason.CUSTOMER_CANCELLED,
                request=request,
            )
    return booking


def provider_cancel_booking(*, booking_id, owner, reason, request=None, now=None):
    """A provider ending an accepted or confirmed booking, with a reason the customer sees. A
    paid booking is refunded in full (FR-025)."""

    now = now or timezone.now()
    reason = (reason or "").strip()
    if not reason:
        raise BookingRefused("Give the customer a reason for cancelling.")
    owned = Booking.objects.filter(shop__owner=owner)
    refresh_bookings(owned.filter(pk=booking_id), now=now)

    with transaction.atomic():
        booking = _locked(owned, booking_id)
        require_bookable_shop(booking.shop)
        _refuse_if_paying(booking)
        unpaid = booking.status == Booking.Status.AWAITING_PAYMENT and _is_unpaid_and_active(
            booking, now
        )
        if not unpaid and booking.status != Booking.Status.CONFIRMED:
            raise _cannot_cancel(booking)
        _cancel(booking, actor=owner, request=request, now=now, reason=reason)
        paid = _paid_record(booking)
        if paid is not None:
            _owe_back(
                paid,
                amount=paid.amount,
                reason=RefundDue.Reason.PROVIDER_CANCELLED,
                note=reason,
                request=request,
            )
    return booking


def admin_cancel_booking(*, booking_id, admin, reason, refund_amount=None, request=None, now=None):
    """An administrator ending any active booking. A paid one is refunded `refund_amount`, which
    defaults to everything paid and can't exceed it."""

    now = now or timezone.now()
    reason = (reason or "").strip()
    if not reason:
        raise BookingRefused("Give a reason for cancelling.")
    refresh_bookings(Booking.objects.filter(pk=booking_id), now=now)

    with transaction.atomic():
        booking = _locked(Booking.objects.all(), booking_id)
        _refuse_if_paying(booking)
        if not (_is_unpaid_and_active(booking, now) or booking.status == Booking.Status.CONFIRMED):
            raise _cannot_cancel(booking)
        paid = _paid_record(booking)
        if paid is None and refund_amount is not None:
            raise BookingRefused("Nothing has been paid for this booking, so there is no refund.")
        if paid is not None:
            amount = paid.amount if refund_amount is None else refund_amount
            if not 0 < amount <= paid.amount:
                raise BookingRefused(f"The refund must be above 0 and at most {paid.amount}.")

        _cancel(booking, actor=admin, request=request, now=now, reason=reason)
        if paid is not None:
            _owe_back(
                paid,
                amount=amount,
                reason=RefundDue.Reason.ADMIN_CANCELLED,
                note=reason,
                request=request,
            )
    return booking


# --- Completion ------------------------------------------------------------------


def _finish_visit(*, booking_id, owner, status, action, request, now):
    """Ends a paid visit once its start time has arrived. The earning fixed at request time then
    becomes available for payout (FR-028). The shop's approval isn't checked: the visit already
    happened, and payouts stay an administrator's decision."""

    now = now or timezone.now()
    with transaction.atomic():
        booking = _locked(Booking.objects.filter(shop__owner=owner), booking_id)
        if booking.status != Booking.Status.CONFIRMED:
            raise BookingConflict(
                f"Only a confirmed booking can be marked; this one is {_status_label(booking)}."
            )
        if booking.starts_at > now:
            raise BookingConflict("This visit hasn't started yet.")
        _change_status(
            booking, status, action=action, actor=owner, request=request, completed_at=now
        )
    return booking


def complete_booking(*, booking_id, owner, request=None, now=None):
    return _finish_visit(
        booking_id=booking_id,
        owner=owner,
        status=Booking.Status.COMPLETED,
        action=AuditAction.BOOKING_COMPLETED,
        request=request,
        now=now,
    )


def mark_no_show(*, booking_id, owner, request=None, now=None):
    """A paid no-show still earns the provider (FR-028)."""

    return _finish_visit(
        booking_id=booking_id,
        owner=owner,
        status=Booking.Status.NO_SHOW,
        action=AuditAction.BOOKING_NO_SHOW,
        request=request,
        now=now,
    )
