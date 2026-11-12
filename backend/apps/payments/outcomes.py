"""Settling asynchronous (mobile-money) payments. `complete_payment()` is the only path that moves
a PENDING `PaymentRecord` to SUCCEEDED/FAILED and its order out of AWAITING_PAYMENT; the AzamPay
callback, the dev simulator and the expiry sweep all go through it.
"""

import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record as record_audit
from apps.cart.models import CartItem
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem, OrderItemStatusEvent
from apps.payments.models import PaymentRecord
from apps.payments.services import (
    LIPA_NAMBA_METHOD,
    MANUAL_METHODS,
    azampay_amount,
)
from apps.realtime.broadcast import publish_on_commit
from apps.realtime.groups import (
    ADMINS,
    booking_audience,
    buyer_groups,
    rider_groups,
    vendor_groups,
)

logger = logging.getLogger(__name__)

EXPIRED_REASON = "The payment request expired before it was confirmed."


def complete_payment(*, record_id, success, provider_reference="", message="", settled_by=None):
    """Idempotent: a record that is no longer PENDING is returned untouched, so a repeated
    callback (or a callback racing the expiry sweep) can't settle a payment twice.

    `settled_by` is the administrator confirming or rejecting a manual payment. A cash-on-delivery
    order is already PLACED, so confirming it only marks the money received.

    The record is locked first and its order or booking second, always in that order (research.md
    §7), so a callback and the booking sweep can't deadlock."""

    with transaction.atomic():
        record = (
            PaymentRecord.objects.select_for_update(of=("self",))
            .select_related("order")
            .get(pk=record_id)
        )
        if record.status != PaymentRecord.Status.PENDING:
            return record

        if provider_reference:
            record.provider_reference = provider_reference
        if settled_by is not None:
            record.settled_by = settled_by
            record.settled_at = timezone.now()
        if success:
            record.status = PaymentRecord.Status.SUCCEEDED
            record.failure_reason = ""
        else:
            record.status = PaymentRecord.Status.FAILED
            record.failure_reason = (message or "Payment was not completed.")[:255]
        record.save()

        was_awaiting = False
        if record.is_booking:
            # Imported here: bookings.services imports this module.
            from apps.bookings.services import on_payment_settled

            on_payment_settled(record, success=success)
        else:
            was_awaiting = _apply_order_outcome(record, success=success)

        # An administrator's manual settlement is audited by its view, with their request.
        if settled_by is None:
            _audit_system_payment(record, success=success, message=message)
        _announce_payment(record, success=success, was_awaiting=was_awaiting)
    return record


def _apply_order_outcome(record, *, success):
    """Moves the order out of AWAITING_PAYMENT (or a COD order's lines to CANCELLED). Returns
    whether the order was awaiting payment, for `_announce_payment`."""

    order = record.order
    was_awaiting = order.status == Order.Status.AWAITING_PAYMENT
    if success:
        order.status = Order.Status.PLACED
        product_ids = order.items.values_list("product_id", flat=True)
        # A guest order's cart is the one it was placed from (guest checkout).
        cart_owner = (
            {"cart__guest_token": order.guest_cart_token}
            if order.is_guest
            else {"cart__customer_id": order.customer_id}
        )
        CartItem.objects.filter(**cart_owner, product_id__in=list(product_ids)).delete()
        if order.is_guest:
            # Imported here: orders.services imports this module.
            from apps.orders.services import send_order_confirmation

            transaction.on_commit(lambda: send_order_confirmation(order))
    else:
        order.status = Order.Status.PAYMENT_FAILED
        _release_order_items(order)
    order.save(update_fields=["status"])
    return was_awaiting


def _audit_system_payment(record, *, success, message):
    if success:
        action = AuditAction.PAYMENT_COMPLETED
    elif message == EXPIRED_REASON:
        action = AuditAction.PAYMENT_EXPIRED
    else:
        action = AuditAction.PAYMENT_FAILED
    if record.is_booking:
        target, target_repr = record.booking, f"Booking #{record.booking_id}"
    else:
        target, target_repr = record.order, f"Order #{record.order_id}"
    record_audit(
        action,
        target=target,
        target_repr=target_repr,
        metadata={
            "reference": record.transaction_reference,
            "method": record.method,
            "amount": record.amount,
            **({} if success else {"reason": record.failure_reason}),
        },
    )


def _announce_payment(record, *, success, was_awaiting):
    """The buyer and administrators always hear about a settled payment. Vendors (and riders)
    hear when the order became theirs to fulfil, or when a rejected cash-on-delivery payment
    cancelled lines they could already see. A booking's audience hears through
    `booking.updated`."""

    if record.is_booking:
        publish_on_commit(
            booking_audience(record.booking),
            {"type": "booking.updated", "booking_id": record.booking_id},
        )
        return

    order_id = record.order_id
    publish_on_commit(
        [*buyer_groups(order_id), ADMINS], {"type": "payment.updated", "order_id": order_id}
    )
    if success and was_awaiting:
        publish_on_commit(vendor_groups(order_id), {"type": "order.created", "order_id": order_id})
    elif not success and not was_awaiting:
        publish_on_commit(
            [*vendor_groups(order_id), *rider_groups(order_id)],
            {"type": "order.updated", "order_id": order_id},
        )


class SettlementError(Exception):
    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


def settle_manual_payment(*, admin, confirm, reason="", order=None, booking=None):
    """An administrator confirming (or rejecting) that a cash-on-delivery or Lipa Namba payment
    actually arrived. Rejecting an order's payment cancels its lines and releases their stock;
    rejecting a booking's leaves the booking waiting for another attempt."""

    if (order is None) == (booking is None):
        raise ValueError("Settle the payment of exactly one order or booking.")
    if order is not None:
        record = PaymentRecord.objects.filter(order=order).first()
    else:
        record = (
            PaymentRecord.objects.filter(booking=booking, status=PaymentRecord.Status.PENDING)
            .order_by("-id")
            .first()
        )
        if record is None:
            raise SettlementError("This booking has no payment waiting to be settled.")
    if record is None or record.method not in MANUAL_METHODS:
        raise SettlementError("Only cash on delivery and Lipa Namba payments are settled by hand.")
    if record.status != PaymentRecord.Status.PENDING:
        raise SettlementError("This payment has already been settled.")
    record = complete_payment(
        record_id=record.id,
        success=confirm,
        message=reason or "Payment was not received.",
        settled_by=admin,
    )
    if record.settled_by_id != admin.id:
        # Settled by someone else (or expired) between our check and our lock.
        raise SettlementError("This payment has already been settled.")
    return record


def _release_order_items(order):
    """Cancels every line of an unpaid order and gives its reserved stock back, locking products
    in id order like checkout does."""

    items = list(order.items.exclude(status=OrderItem.Status.CANCELLED).order_by("product_id"))
    products = {
        product.id: product
        for product in Product.all_objects.select_for_update(of=("self",))
        .filter(id__in=[item.product_id for item in items])
        .order_by("id")
    }
    for item in items:
        product = products[item.product_id]
        product.stock_quantity += item.quantity
        product.save(update_fields=["stock_quantity"])
        item.status = OrderItem.Status.CANCELLED
        item.save(update_fields=["status"])
        OrderItemStatusEvent.objects.create(order_item=item, status=OrderItem.Status.CANCELLED)


def _parse_amount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def handle_azampay_callback(payload):
    """Applies an AzamPay MNO checkout callback. Returns a short outcome string for logging; never
    raises on bad input, since AzamPay would just keep retrying."""

    if not isinstance(payload, dict):
        return "ignored: not an object"
    reference = str(payload.get("utilityref") or "")
    record = PaymentRecord.objects.filter(transaction_reference=reference).first()
    if record is None:
        logger.warning("AzamPay callback for unknown reference %r", reference)
        return "ignored: unknown reference"

    amount = _parse_amount(payload.get("amount"))
    if amount is None or amount != Decimal(azampay_amount(record.amount)):
        logger.warning(
            "AzamPay callback for %s has amount %r, expected %s; ignoring",
            reference,
            payload.get("amount"),
            record.amount,
        )
        return "ignored: amount mismatch"

    success = str(payload.get("transactionstatus") or "").lower() == "success"
    if success and record.is_booking and record.status == PaymentRecord.Status.FAILED:
        # Money that arrived after we gave up on it: confirm the booking or owe it back.
        from apps.bookings.services import reconcile_late_payment

        reconcile_late_payment(
            record_id=record.id, provider_reference=str(payload.get("reference") or "")
        )
        return "reconciled late payment"
    record = complete_payment(
        record_id=record.id,
        success=success,
        provider_reference=str(payload.get("reference") or ""),
        message=str(payload.get("message") or ""),
    )
    return f"settled: {record.status}"


def expire_stale_payments(*, queryset=None):
    """Fails every PENDING mobile-money payment older than `PAYMENT_PENDING_TIMEOUT_MINUTES` and
    Lipa Namba payment older than `MANUAL_PAYMENT_TIMEOUT_HOURS`. Cash on delivery never expires:
    its goods are already on their way. Returns how many were expired."""

    now = timezone.now()
    mobile_cutoff = now - timedelta(minutes=settings.PAYMENT_PENDING_TIMEOUT_MINUTES)
    manual_cutoff = now - timedelta(hours=settings.MANUAL_PAYMENT_TIMEOUT_HOURS)
    stale = (queryset if queryset is not None else PaymentRecord.objects).filter(
        # A booking's Lipa Namba payment waits for an administrator however long it takes, so
        # money that did arrive is never failed unchecked (research.md §4).
        Q(method=LIPA_NAMBA_METHOD, created_at__lte=manual_cutoff, booking__isnull=True)
        | (~Q(method__in=MANUAL_METHODS) & Q(created_at__lte=mobile_cutoff)),
        status=PaymentRecord.Status.PENDING,
    )
    expired = 0
    for record_id in stale.values_list("id", flat=True):
        record = complete_payment(record_id=record_id, success=False, message=EXPIRED_REASON)
        if record.failure_reason == EXPIRED_REASON:
            expired += 1
    return expired
