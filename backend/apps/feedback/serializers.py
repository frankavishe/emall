from rest_framework import serializers

from apps.feedback.models import Review


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
