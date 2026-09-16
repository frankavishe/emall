from rest_framework import serializers

from apps.vendors.models import Shop


class ShopBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "status"]
        read_only_fields = fields


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "status", "status_reason", "created_at"]
        read_only_fields = ["id", "status", "status_reason", "created_at"]

    def validate_name(self, value):
        if Shop.objects.filter(name=value).exists():
            raise serializers.ValidationError("A shop with this name already exists.")
        return value

    def create(self, validated_data):
        return Shop.objects.create(owner=self.context["request"].user, **validated_data)


class AdminShopListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "status",
            "status_reason",
            "created_at",
            "owner_name",
            "owner_email",
        ]
        read_only_fields = fields
