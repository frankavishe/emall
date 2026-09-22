from rest_framework import serializers

from apps.feedback.models import Review


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
