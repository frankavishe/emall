from django.conf import settings
from django.db import models


class Review(models.Model):
    """A single Customer's feedback on a single Product. At most one row per (customer, product)
    pair (data-model.md) — enforced create-or-update at the view layer, guaranteed here by
    `unique_review_per_customer_product`. Eligibility (a DELIVERED OrderItem for this product)
    is checked live at write time, not stored on this row (research.md §2)."""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"], name="unique_review_per_customer_product"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_range",
            ),
        ]

    def __str__(self):
        return f"Review({self.customer_id} -> {self.product_id}, {self.rating}*)"
