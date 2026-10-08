from django.db import models

from apps.core.uploads import UniqueUploadTo


class Category(models.Model):
    """Global, Administrator-owned classification list, two levels deep: top-level categories
    (`parent` is null) and their subcategories. Managed through `/api/admin/categories`.
    Vendors list a product under a subcategory, or directly under a top-level category only
    while it has no subcategories (VendorProductWriteSerializer.validate_category).
    """

    name = models.CharField(max_length=100)
    # Globally unique (not per parent): public catalog filters address a category by slug alone.
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"], name="unique_category_name_per_parent"
            ),
            # NULLs are distinct in the constraint above, so top-level names need their own.
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(parent__isnull=True),
                name="unique_top_level_category_name",
            ),
        ]

    def __str__(self):
        if self.parent_id:
            return f"{self.parent.name} › {self.name}"
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
    image = models.ImageField(upload_to=UniqueUploadTo("products"))
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product.name} image #{self.position}"
