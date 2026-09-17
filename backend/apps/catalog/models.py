from django.db import models


class Category(models.Model):
    """Global, Administrator-owned classification list (spec.md Assumptions). This feature only
    reads/seeds it — no CRUD endpoint exists here.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class ProductManager(models.Manager):
    """Excludes soft-deleted rows from every queryset (research.md §4) so no call site — vendor
    or public — has to remember to filter `is_deleted` itself (FR-014).
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Product(models.Model):
    shop = models.ForeignKey(
        "vendors.Shop", on_delete=models.CASCADE, related_name="products"
    )
    # Nullable: a draft only needs `name` at creation time (FR-001/FR-002 require the *fields
    # you send* to be valid, not that all of them be sent yet). The remaining fields here may be
    # filled in later via PATCH; `publish()` re-checks they're all present (FR-004, Edge Cases).
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # PositiveIntegerField is non-negative by type (FR-012) and is the decrementable counter a
    # future checkout feature will need (FR-015). Nullable so "missing" (None) is distinguishable
    # from "explicitly zero" (a valid, published, out-of-stock product — FR-011).
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "name"], name="unique_product_name_per_shop"
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0) | models.Q(price__isnull=True),
                name="product_price_non_negative",
            ),
        ]

    def __str__(self):
        return self.name

    def missing_fields_for_publish(self):
        missing = []
        if not self.description:
            missing.append("description")
        if self.price is None:
            missing.append("price")
        if self.stock_quantity is None:
            missing.append("stock_quantity")
        if self.category_id is None:
            missing.append("category")
        return missing


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product.name} image #{self.position}"
