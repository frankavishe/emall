from django.db.models import Avg, Count, Max
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, PermissionDenied

from apps.catalog.models import Category, Product, ProductImage
from apps.feedback.serializers import ReviewDisplaySerializer
from apps.vendors.models import Shop
from apps.vendors.serializers import ShopBriefSerializer, ShopLogoUrlMixin, shop_logo_url


class ReviewAggregateMixin:
    """Shared `average_rating`/`review_count` computation for the public catalog serializers
    (research.md §4 — computed on read, never denormalized on `Product`)."""

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(value=Avg("rating"))["value"]

    def get_review_count(self, obj):
        return obj.reviews.aggregate(value=Count("id"))["value"]


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Category
        fields = ["name", "slug", "parent"]
        read_only_fields = fields


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Public category list: top-level categories, each with its subcategories."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["name", "slug", "children"]
        read_only_fields = fields

    def get_children(self, obj):
        return [{"name": c.name, "slug": c.slug} for c in obj.children.all()]


class CategoryConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This change conflicts with existing categories or products."
    default_code = "conflict"


class AdminCategorySerializer(serializers.ModelSerializer):
    """`product_count` counts live products; `can_delete` also accounts for soft-deleted ones,
    which still reference the category (Product.category is PROTECT). Both come from
    annotations on catalog.views._admin_categories()."""

    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    product_count = serializers.IntegerField(read_only=True)
    can_delete = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "product_count", "can_delete", "children"]
        read_only_fields = fields

    def get_can_delete(self, obj):
        return obj.all_product_count == 0 and obj.child_count == 0

    def get_children(self, obj):
        children = self.context.get("children", {}).get(obj.id, [])
        return AdminCategorySerializer(children, many=True, context=self.context).data


def unique_category_slug(name, parent):
    base = slugify(name) or "category"
    if Category.objects.filter(slug=base).exists() and parent is not None:
        base = f"{parent.slug}-{base}"
    slug, n = base, 2
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class AdminCategoryWriteSerializer(serializers.ModelSerializer):
    """Create/rename/move. The slug is generated once on create and kept on rename, so existing
    catalog links keep working."""

    name = serializers.CharField(max_length=100)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Category
        fields = ["name", "parent"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter a category name.")
        return value

    def validate(self, attrs):
        instance = self.instance
        name = attrs.get("name", getattr(instance, "name", None))
        parent = attrs["parent"] if "parent" in attrs else getattr(instance, "parent", None)

        if parent is not None:
            if instance is not None and parent.pk == instance.pk:
                raise serializers.ValidationError({"parent": "A category can't be its own parent."})
            if parent.parent_id is not None:
                raise serializers.ValidationError(
                    {"parent": "Subcategories can't have subcategories of their own."}
                )
            if instance is not None and instance.children.exists():
                raise serializers.ValidationError(
                    {"parent": f"{instance.name} has subcategories, so it must stay top-level."}
                )
            gains_child = instance is None or instance.parent_id != parent.pk
            if gains_child and Product.all_objects.filter(category=parent).exists():
                raise CategoryConflict(
                    f"Products are listed directly under {parent.name}. Move them to another "
                    "category before adding subcategories to it."
                )

        siblings = Category.objects.filter(parent=parent, name__iexact=name)
        if instance is not None:
            siblings = siblings.exclude(pk=instance.pk)
        if siblings.exists():
            where = f"under {parent.name}" if parent else "at the top level"
            raise serializers.ValidationError({"name": f"A category named {name} already exists {where}."})
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = unique_category_slug(
            validated_data["name"], validated_data.get("parent")
        )
        return super().create(validated_data)


class ProductImageReadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "position"]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


MAX_PRODUCT_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MAX_PRODUCT_IMAGES = 10


class VendorProductWriteSerializer(serializers.ModelSerializer):
    """Create/update for the Vendor-owned side. `shop_id` is required on create (validated
    against ownership + approval — FR-002) and ignored on update (a product's shop is immutable
    after creation)."""

    shop_id = serializers.PrimaryKeyRelatedField(
        source="shop", queryset=Shop.objects.all(), write_only=True, required=False
    )
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    # Update-only: ids of this product's existing images to delete. Ids belonging to other
    # products are ignored (the delete is scoped to the instance).
    remove_image_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "shop_id",
            "name",
            "description",
            "price",
            "stock_quantity",
            "category",
            "images",
            "remove_image_ids",
            "is_published",
        ]
        read_only_fields = ["id", "is_published"]
        extra_kwargs = {
            "description": {"required": False},
            "price": {"required": False, "allow_null": True},
            "stock_quantity": {"required": False, "allow_null": True},
        }

    def validate_category(self, value):
        if value is not None and value.children.exists():
            raise serializers.ValidationError(f"Choose a subcategory of {value.name}.")
        return value

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_stock_quantity(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value

    def validate_images(self, value):
        for image in value:
            if image.size > MAX_PRODUCT_IMAGE_SIZE_BYTES:
                max_mb = MAX_PRODUCT_IMAGE_SIZE_BYTES // (1024 * 1024)
                raise serializers.ValidationError(f"Each image must be {max_mb}MB or smaller.")
        return value

    def validate(self, attrs):
        request = self.context["request"]

        if self.instance is None:
            shop = attrs.get("shop")
            if shop is None:
                raise serializers.ValidationError({"shop_id": "This field is required."})
            if shop.owner_id != request.user.id or shop.status != Shop.Status.APPROVED:
                raise PermissionDenied(
                    "You can only create products under an approved shop you own."
                )
        else:
            # shop is immutable after creation — silently ignore if a caller sends it anyway.
            attrs.pop("shop", None)
            shop = self.instance.shop

        name = attrs.get("name", getattr(self.instance, "name", None))
        if name:
            duplicate = Product.objects.filter(shop=shop, name=name)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"name": "A product with this name already exists in this shop."}
                )

        new_count = len(attrs.get("images", []))
        if self.instance is None:
            total = new_count
        else:
            remove_ids = set(attrs.get("remove_image_ids", []))
            kept = self.instance.images.exclude(id__in=remove_ids).count()
            total = kept + new_count
        if total > MAX_PRODUCT_IMAGES:
            raise serializers.ValidationError(
                {"images": f"A product can have at most {MAX_PRODUCT_IMAGES} images."}
            )

        return attrs

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        validated_data.pop("remove_image_ids", None)
        product = Product.objects.create(**validated_data)
        for position, image in enumerate(images):
            ProductImage.objects.create(product=product, image=image, position=position)
        return product

    def update(self, instance, validated_data):
        images = validated_data.pop("images", [])
        remove_ids = validated_data.pop("remove_image_ids", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if remove_ids:
            for product_image in instance.images.filter(id__in=remove_ids):
                product_image.image.delete(save=False)
                product_image.delete()
        if images:
            # Append after the current last image rather than replacing the gallery.
            last = instance.images.aggregate(value=Max("position"))["value"]
            start = 0 if last is None else last + 1
            for offset, image in enumerate(images):
                ProductImage.objects.create(
                    product=instance, image=image, position=start + offset
                )
        return instance


class CatalogShopSerializer(ShopLogoUrlMixin, serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ["id", "name", "logo_url", "primary_color", "accent_color"]
        read_only_fields = fields


class CatalogProductListSerializer(ReviewAggregateMixin, serializers.ModelSerializer):
    """Public list shape (contracts/catalog-api.md) — never exposes the raw `stock_quantity`,
    only the derived `in_stock` boolean (FR-011). Carries the aggregate rating (FR-006) but not
    the full `reviews` list, which is detail-only (contracts/feedback-api.md)."""

    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    in_stock = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    shop_logo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "category",
            "in_stock",
            "shop_name",
            "shop_logo_url",
            "thumbnail_url",
            "average_rating",
            "review_count",
        ]
        read_only_fields = fields

    def get_in_stock(self, obj):
        return bool(obj.stock_quantity)

    def get_shop_logo_url(self, obj):
        return shop_logo_url(obj.shop, self.context.get("request"))

    def get_thumbnail_url(self, obj):
        image = obj.images.first()
        if not image:
            return None
        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class CatalogProductDetailSerializer(ReviewAggregateMixin, serializers.ModelSerializer):
    """Public detail shape (contracts/catalog-api.md) — `stock_status` is derived, the raw
    `stock_quantity` count is never exposed (FR-011). Adds the aggregate rating and the full
    `reviews` list (FR-005, FR-006)."""

    category = CategorySerializer(read_only=True)
    stock_status = serializers.SerializerMethodField()
    shop = CatalogShopSerializer(read_only=True)
    images = ProductImageReadSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "category",
            "stock_status",
            "shop",
            "images",
            "average_rating",
            "review_count",
            "reviews",
        ]
        read_only_fields = fields

    def get_stock_status(self, obj):
        return "in_stock" if obj.stock_quantity else "out_of_stock"

    def get_reviews(self, obj):
        queryset = obj.reviews.select_related("customer").order_by("-created_at")
        return ReviewDisplaySerializer(queryset, many=True).data


class VendorProductListSerializer(serializers.ModelSerializer):
    """Read shape for the Vendor's own product list/detail. Includes `description` (beyond what
    contracts/catalog-api.md's list example shows) so the frontend edit page can prefill a form
    from this same response without a separate detail endpoint."""

    shop = ShopBriefSerializer(read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    images = ProductImageReadSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "shop",
            "name",
            "description",
            "price",
            "stock_quantity",
            "category",
            "is_published",
            "images",
        ]
        read_only_fields = fields
