"""Checkout business logic (research.md §4). `place_order()` is the only way an `Order` is ever
created — no view constructs one directly.
"""

import logging
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product
from apps.core.email import get_email_service
from apps.delivery.pricing import DeliveryError, quote_delivery
from apps.finance.services import split_line
from apps.orders.models import Order, OrderDelivery, OrderItem, OrderItemStatusEvent
from apps.payments.models import PaymentRecord
from apps.payments.outcomes import complete_payment, expire_stale_payments
from apps.payments.services import (
    MOBILE_MONEY_METHOD,
    InitiationResult,
    get_mobile_money_gateway,
    get_payment_service,
    mobile_money_enabled,
)

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    """Raised for every checkout failure case; the view translates `code` into the contract's
    `400` response shapes (contracts/cart-checkout-api.md)."""

    def __init__(self, code, detail, **extra):
        self.code = code
        self.detail = detail
        self.extra = extra
        super().__init__(detail)


class TransitionError(Exception):
    """Raised when a requested `OrderItem.status` transition isn't the single valid next step
    (research.md §1); the view translates this into the contract's `400` response shape
    (contracts/order-fulfillment-api.md)."""

    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail)


# Fixed adjacency map (FR-002, FR-003, data-model.md): only these (current, requested) pairs are
# valid. Any other pair — backward, skipped, from a terminal state, or SHIPPED->CANCELLED — is
# rejected with no write.
_VALID_TRANSITIONS = {
    OrderItem.Status.PENDING: {OrderItem.Status.PROCESSING, OrderItem.Status.CANCELLED},
    OrderItem.Status.PROCESSING: {OrderItem.Status.SHIPPED, OrderItem.Status.CANCELLED},
    OrderItem.Status.SHIPPED: {OrderItem.Status.DELIVERED},
    OrderItem.Status.DELIVERED: set(),
    OrderItem.Status.CANCELLED: set(),
}


def _notify_order_item_status_change(order_item):
    """Best-effort side effect of a committed status change (research.md §1, §2). Any failure
    here is caught and logged, never propagated — a notification problem must never look like a
    failure of the (already-committed) status transition itself (FR-005)."""

    try:
        get_email_service().send_order_item_status_email(order_item)
    except Exception:
        logger.exception(
            "Failed to send order item status notification for order_item_id=%s", order_item.id
        )


def advance_order_item_status(*, order_item, new_status):
    """The only path that ever changes `OrderItem.status` (data-model.md). Validates the
    requested transition against `_VALID_TRANSITIONS` before writing anything; on a valid
    transition to CANCELLED, restores the line's quantity to the product's stock in the same
    atomic transaction (FR-011, research.md §2)."""

    current_status = order_item.status
    if new_status not in _VALID_TRANSITIONS.get(current_status, set()):
        raise TransitionError(f"Cannot move {current_status} to {new_status}.")

    with transaction.atomic():
        if new_status == OrderItem.Status.CANCELLED:
            product = (
                Product.objects.select_for_update(of=("self",))
                .get(pk=order_item.product_id)
            )
            product.stock_quantity += order_item.quantity
            product.save(update_fields=["stock_quantity"])

        order_item.status = new_status
        order_item.save(update_fields=["status"])
        OrderItemStatusEvent.objects.create(order_item=order_item, status=new_status)
        transaction.on_commit(lambda: _notify_order_item_status_change(order_item))

    return order_item


class AssignmentError(Exception):
    """Raised when a rider can't be (un)assigned to an order line."""

    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail)


# A line can only be handed to a rider once the vendor is preparing it, and until it's delivered.
ASSIGNABLE_STATUSES = {OrderItem.Status.PROCESSING, OrderItem.Status.SHIPPED}


def assign_rider(*, order_item, rider):
    """Assigns `rider` to `order_item`, or unassigns when `rider` is None."""

    if order_item.status not in ASSIGNABLE_STATUSES:
        raise AssignmentError(
            f"Only processing or shipped lines can be assigned (this one is {order_item.status})."
        )
    if rider is not None and (rider.role != User.Role.RIDER or not rider.is_active):
        raise AssignmentError("That rider is not an active rider.")

    order_item.rider = rider
    order_item.rider_assigned_at = timezone.now() if rider is not None else None
    order_item.save(update_fields=["rider", "rider_assigned_at"])
    return order_item


def _delivery_legs(cart_items, latitude, longitude):
    try:
        return quote_delivery([item.product.shop for item in cart_items], latitude, longitude)
    except DeliveryError as error:
        raise CheckoutError(error.code, error.detail) from error


def quote_cart_delivery(*, customer, latitude, longitude):
    """The delivery quote shown at checkout (007-delivery-fee). Advisory only: `place_order()`
    recomputes it from current data when the order is actually placed."""

    cart_items = list(
        CartItem.objects.select_related("product__shop")
        .filter(cart__customer=customer)
        .order_by("product_id")
    )
    if not cart_items:
        raise CheckoutError("empty_cart", "Your cart is empty.")

    legs = _delivery_legs(cart_items, latitude, longitude)
    items_subtotal = sum((item.subtotal for item in cart_items), Decimal("0.00"))
    delivery_fee = sum((leg.fee for leg in legs), Decimal("0.00"))
    return {
        "legs": legs,
        "items_subtotal": items_subtotal,
        "delivery_fee": delivery_fee,
        "total": items_subtotal + delivery_fee,
    }


def _locked_cart_items(customer):
    """The customer's cart lines with their products row-locked and re-validated. Caller holds
    the transaction."""

    cart_items = list(
        CartItem.objects.select_related("product__shop")
        .filter(cart__customer=customer)
        .order_by("product_id")
    )
    if not cart_items:
        raise CheckoutError("empty_cart", "Your cart is empty.")

    # Lock only the touched Product rows, always in ascending product_id order, to avoid
    # deadlocking against a concurrent checkout that shares a product (research.md §4).
    product_ids = sorted({item.product_id for item in cart_items})
    locked_products = {
        product.id: product
        for product in Product.objects.select_related("shop")
        .select_for_update(of=("self",))
        .filter(id__in=product_ids)
        .order_by("id")
    }
    for item in cart_items:
        item.product = locked_products[item.product_id]

    unavailable = [
        {"cart_item_id": item.id, "reason": item.unavailable_reason}
        for item in cart_items
        if item.unavailable_reason
    ]
    if unavailable:
        raise CheckoutError(
            "unavailable_lines",
            "Some items in your cart are no longer available.",
            lines=unavailable,
        )
    return cart_items


def _price(cart_items, shipping_data):
    # Delivery is mandatory and always priced here from current shop locations and
    # settings, never from a client-sent fee (007-delivery-fee FR-010).
    legs = _delivery_legs(cart_items, shipping_data["latitude"], shipping_data["longitude"])
    delivery_fee = sum((leg.fee for leg in legs), Decimal("0.00"))
    items_subtotal = sum((item.subtotal for item in cart_items), Decimal("0.00"))
    return legs, delivery_fee, items_subtotal + delivery_fee


def _create_order(*, customer, shipping_data, status, cart_items, legs, delivery_fee):
    """Creates the order, its delivery legs and lines, and takes the lines' stock. Caller holds
    the transaction and the product locks."""

    order = Order.objects.create(
        customer=customer,
        status=status,
        delivery_fee=delivery_fee,
        **shipping_data,
    )
    OrderDelivery.objects.bulk_create(
        OrderDelivery(order=order, shop=leg.shop, distance_km=leg.distance_km, fee=leg.fee)
        for leg in legs
    )
    # The customer pays the mall; each line freezes the mall's commission and what the mall
    # owes the shop, at the shop's commission rate as of now.
    rates = {}
    for item in cart_items:
        shop = item.product.shop
        if shop.id not in rates:
            rates[shop.id] = shop.effective_commission_rate()
        commission, vendor_earning = split_line(item.subtotal, rates[shop.id])
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.product.price,
            status=OrderItem.Status.PENDING,
            commission_rate=rates[shop.id],
            commission_amount=commission,
            vendor_earning=vendor_earning,
        )
        item.product.stock_quantity -= item.quantity
        item.product.save(update_fields=["stock_quantity"])
    return order


def place_order(*, customer, shipping_data, payment_method, msisdn=None, provider=None):
    """Mobile money (when a mobile-money `PAYMENT_BACKEND` is configured) returns an
    AWAITING_PAYMENT order whose payment the gateway confirms later; every other method is
    charged synchronously and returns a PLACED order."""

    if payment_method == MOBILE_MONEY_METHOD and mobile_money_enabled():
        return _place_mobile_money_order(
            customer=customer, shipping_data=shipping_data, msisdn=msisdn, provider=provider
        )

    with transaction.atomic():
        cart_items = _locked_cart_items(customer)
        legs, delivery_fee, total = _price(cart_items, shipping_data)
        payment_result = get_payment_service().charge(amount=total, method=payment_method)
        if not payment_result.success:
            raise CheckoutError("payment_failed", "Payment was declined.")

        order = _create_order(
            customer=customer,
            shipping_data=shipping_data,
            status=Order.Status.PLACED,
            cart_items=cart_items,
            legs=legs,
            delivery_fee=delivery_fee,
        )
        PaymentRecord.objects.create(
            order=order,
            method=payment_method,
            amount=total,
            status=PaymentRecord.Status.SUCCEEDED,
            transaction_reference=payment_result.transaction_reference,
        )

        CartItem.objects.filter(cart__customer=customer).delete()

    return order


def _place_mobile_money_order(*, customer, shipping_data, msisdn, provider):
    """Reserves the stock under an AWAITING_PAYMENT order, then (after commit, outside the row
    locks) asks the gateway to push a payment prompt to the customer's phone. The cart is kept
    until the payment succeeds, so a failed payment loses nothing."""

    # A payment that timed out shouldn't block the customer from trying again.
    expire_stale_payments(queryset=PaymentRecord.objects.filter(order__customer=customer))

    with transaction.atomic():
        # Serialises this customer's checkouts so two can't both pass the pending check.
        Cart.objects.select_for_update().filter(customer=customer).first()
        pending = Order.objects.filter(
            customer=customer, status=Order.Status.AWAITING_PAYMENT
        ).first()
        if pending is not None:
            raise CheckoutError(
                "payment_pending",
                "You already have an order waiting for payment.",
                order_id=pending.id,
            )

        cart_items = _locked_cart_items(customer)
        legs, delivery_fee, total = _price(cart_items, shipping_data)
        order = _create_order(
            customer=customer,
            shipping_data=shipping_data,
            status=Order.Status.AWAITING_PAYMENT,
            cart_items=cart_items,
            legs=legs,
            delivery_fee=delivery_fee,
        )
        record = PaymentRecord.objects.create(
            order=order,
            method=MOBILE_MONEY_METHOD,
            amount=total,
            status=PaymentRecord.Status.PENDING,
            transaction_reference=uuid.uuid4().hex,
            provider=provider,
            msisdn=msisdn,
        )

    try:
        result = get_mobile_money_gateway().initiate(
            amount=total,
            msisdn=msisdn,
            provider=provider,
            external_id=record.transaction_reference,
        )
    except Exception:
        logger.exception("Mobile money initiation crashed for order %s", order.id)
        result = InitiationResult(accepted=False, message="Payment provider unavailable.")

    if not result.accepted:
        complete_payment(record_id=record.id, success=False, message=result.message)
        raise CheckoutError(
            "payment_failed",
            result.message or "The payment request could not be sent.",
            order_id=order.id,
        )

    if result.provider_reference:
        PaymentRecord.objects.filter(pk=record.pk).update(
            provider_reference=result.provider_reference
        )
    order.refresh_from_db()
    return order
