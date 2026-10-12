from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    """Created only by `orders.services.place_order()` inside the atomic checkout transaction
    (research.md §4) — never via a generic create endpoint that accepts arbitrary
    `status`/`placed_at`.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLACED
    )
    recipient_name = models.CharField(max_length=255)
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=32)
    country = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    # Delivery pin and fee (007-delivery-fee). Null/zero only on orders placed before delivery
    # pricing existed; `place_order()` always sets them.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    placed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order({self.pk}, {self.customer_id})"

    @property
    def items_subtotal(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))

    @property
    def total(self):
        return self.items_subtotal + self.delivery_fee


class OrderDelivery(models.Model):
    """One delivery leg of an `Order`: the fee charged to bring one shop's items to the customer,
    frozen at checkout by `place_order()` so later pricing or shop-location edits don't rewrite
    it. The order's `delivery_fee` is the sum of its legs."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="deliveries")
    shop = models.ForeignKey("vendors.Shop", on_delete=models.PROTECT, related_name="+")
    distance_km = models.DecimalField(max_digits=7, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "shop"], name="unique_order_delivery_shop"),
        ]

    def __str__(self):
        return f"OrderDelivery(order={self.order_id}, shop={self.shop_id}, {self.fee})"


class OrderItem(models.Model):
    """One line of an `Order`, frozen at purchase time. `unit_price` never re-reads `product.
    price` after creation (research.md §2) — only `CartItem` does that.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    # Delivery rider, set only by `orders.services.assign_rider()`.
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        limit_choices_to={"role": "RIDER"},
    )
    rider_assigned_at = models.DateTimeField(null=True, blank=True)

    # Money split, frozen at checkout by `place_order()`: the customer pays the mall `subtotal`,
    # the mall keeps `commission_amount` (`commission_rate` percent) and owes the shop
    # `vendor_earning`. The earning becomes payable once the line is DELIVERED.
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Set once the earning is included in a payout; cleared again if that payout fails.
    payout = models.ForeignKey(
        "finance.Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    def __str__(self):
        return f"{self.product_id} x{self.quantity} (order {self.order_id})"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class OrderItemStatusEvent(models.Model):
    """One row per `OrderItem.status` change, written only by
    `orders.services.advance_order_item_status()` in the same transaction as the status write
    (data-model.md). Append-only — never updated or deleted once created. Visible only to
    Administrators (Clarifications session 2026-09-21).
    """

    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name="status_events"
    )
    status = models.CharField(max_length=20, choices=OrderItem.Status.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OrderItem({self.order_item_id}) -> {self.status}"
