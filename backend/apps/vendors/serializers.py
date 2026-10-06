from rest_framework import serializers

from apps.vendors.models import Shop

MAX_SHOP_LOGO_SIZE_BYTES = 2 * 1024 * 1024


def shop_logo_url(shop, request):
    """Absolute URL of a shop's logo, or None if it has none."""
    if not shop.logo:
        return None
    url = shop.logo.url
    return request.build_absolute_uri(url) if request else url


class ShopLogoUrlMixin:
    def get_logo_url(self, obj):
        return shop_logo_url(obj, self.context.get("request"))


class ShopBriefSerializer(ShopLogoUrlMixin, serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ["id", "name", "status", "logo_url", "primary_color", "accent_color"]
        read_only_fields = fields


class ShopSerializer(ShopLogoUrlMixin, serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "status",
            "status_reason",
            "created_at",
            "logo_url",
            "primary_color",
            "accent_color",
        ]
        read_only_fields = [
            "id",
            "status",
            "status_reason",
            "created_at",
            "primary_color",
            "accent_color",
        ]

    def validate_name(self, value):
        if Shop.objects.filter(name=value).exists():
            raise serializers.ValidationError("A shop with this name already exists.")
        return value

    def create(self, validated_data):
        return Shop.objects.create(owner=self.context["request"].user, **validated_data)


class ShopLogoSerializer(serializers.Serializer):
    logo = serializers.ImageField()

    def validate_logo(self, value):
        if value.size > MAX_SHOP_LOGO_SIZE_BYTES:
            max_mb = MAX_SHOP_LOGO_SIZE_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"The logo must be {max_mb}MB or smaller.")
        return value


class ShopThemeSerializer(serializers.ModelSerializer):
    """Partial update of a shop's colors. Each is `#rrggbb` (stored lowercase) or `""` to fall
    back to the MangiMall default."""

    class Meta:
        model = Shop
        fields = ["primary_color", "accent_color"]

    def validate_primary_color(self, value):
        return value.lower()

    def validate_accent_color(self, value):
        return value.lower()


class AdminShopListSerializer(ShopLogoUrlMixin, serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    logo_url = serializers.SerializerMethodField()

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
            "logo_url",
        ]
        read_only_fields = fields
