"""Checkout business logic (research.md §4). `place_order()` is the only way an `Order` is ever
created — no view constructs one directly.
"""

from decimal import Decimal

from django.db import transaction

from apps.cart.models import CartItem
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
from apps.payments.services import get_payment_service


class CheckoutError(Exception):
    """Raised for every checkout failure case; the view translates `code` into the contract's
    `400` response shapes (contracts/cart-checkout-api.md)."""

    def __init__(self, code, detail, **extra):
        self.code = code
        self.detail = detail
        self.extra = extra
        super().__init__(detail)


def place_order(*, customer, shipping_data, payment_method):
    with transaction.atomic():
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

        total = sum((item.subtotal for item in cart_items), Decimal("0.00"))
        payment_result = get_payment_service().charge(amount=total, method=payment_method)
        if not payment_result.success:
            raise CheckoutError("payment_failed", "Payment was declined.")

        order = Order.objects.create(
            customer=customer, status=Order.Status.PLACED, **shipping_data
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
                status=OrderItem.Status.PENDING,
            )
            item.product.stock_quantity -= item.quantity
            item.product.save(update_fields=["stock_quantity"])

        PaymentRecord.objects.create(
            order=order,
            method=payment_method,
            status=PaymentRecord.Status.SUCCEEDED,
            transaction_reference=payment_result.transaction_reference,
        )

        CartItem.objects.filter(cart__customer=customer).delete()

    return order
