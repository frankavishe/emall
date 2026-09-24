from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.feedback.models import Review
from apps.vendors.models import Shop


def customer_display_name(customer):
    """First name plus last-initial, e.g. "Ama Owusu" -> "Ama O." (FR-005 — reviews are
    attributed without exposing a customer's full name to other shoppers)."""

    parts = customer.name.split()
    if len(parts) <= 1:
        return customer.name
    return f"{parts[0]} {parts[-1][0]}."


class ReviewWriteSerializer(serializers.ModelSerializer):
    """Create-or-update shape for the Customer's own review (FR-001, FR-003 upsert;
    research.md §3). `rating` is required; `comment` is optional and defaults to ""."""

    class Meta:
        model = Review
        fields = ["id", "product", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "product", "created_at", "updated_at"]
        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
        }


class ReviewDisplaySerializer(serializers.ModelSerializer):
    """Public read shape embedded in the catalog product detail response (FR-005;
    contracts/feedback-api.md)."""

    customer_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "customer_display_name", "rating", "comment", "created_at"]
        read_only_fields = fields

    def get_customer_display_name(self, obj):
        return customer_display_name(obj.customer)


class _ProductRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name"]
        read_only_fields = fields


class _ShopRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name"]
        read_only_fields = fields


class _CustomerRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email"]
        read_only_fields = fields


class VendorReviewSerializer(serializers.ModelSerializer):
    """Read-only shape for a Vendor's own-shop feedback view (FR-007, FR-009;
    contracts/feedback-api.md)."""

    product = _ProductRefSerializer(read_only=True)
    customer_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "product", "customer_display_name", "rating", "comment", "created_at"]
        read_only_fields = fields

    def get_customer_display_name(self, obj):
        return customer_display_name(obj.customer)


class AdminReviewSerializer(serializers.ModelSerializer):
    """Read-only shape for Administrator moderation, exposing product/shop/customer identity
    across every shop (FR-010; contracts/feedback-api.md)."""

    product = _ProductRefSerializer(read_only=True)
    shop = _ShopRefSerializer(source="product.shop", read_only=True)
    customer = _CustomerRefSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "product", "shop", "customer", "rating", "comment", "created_at"]
        read_only_fields = fields
