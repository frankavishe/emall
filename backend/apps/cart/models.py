from django.conf import settings
from django.db import models

from apps.vendors.models import Shop


class Cart(models.Model):
    """Exactly one active cart per Customer account (spec Key Entities); created lazily via
    `get_or_create` on first access (research.md §1), never at registration time.
    """

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart({self.customer_id})"


class CartItem(models.Model):
    """A line within a Cart. Deliberately has no `unit_price` column — price is always read live
    from the current `Product` (research.md §2), never frozen until an Order actually exists.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart")
        ]

    def __str__(self):
        return f"{self.product_id} x{self.quantity} (cart {self.cart_id})"

    @property
    def unit_price(self):
        return self.product.price

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    @property
    def unavailable_reason(self):
        """Returns `None` when the line is available, otherwise the reason it isn't — checked in
        this order so the first applicable reason wins (data-model.md, research.md §6).
        """
        product = self.product
        if product.is_deleted or not product.is_published:
            return "no longer published"
        if product.shop.status != Shop.Status.APPROVED:
            return "shop is no longer approved"
        if self.quantity > (product.stock_quantity or 0):
            return "quantity exceeds available stock"
        return None

    @property
    def is_available(self):
        return self.unavailable_reason is None
