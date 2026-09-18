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
    placed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order({self.pk}, {self.customer_id})"

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))


class OrderItem(models.Model):
    """One line of an `Order`, frozen at purchase time. `unit_price` never re-reads `product.
    price` after creation (research.md §2) — only `CartItem` does that.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"{self.product_id} x{self.quantity} (order {self.order_id})"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
