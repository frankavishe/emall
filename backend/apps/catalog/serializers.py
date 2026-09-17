from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.catalog.models import Category, Product, ProductImage
from apps.vendors.models import Shop
from apps.vendors.serializers import ShopBriefSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name", "slug"]
        read_only_fields = fields


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
            "is_published",
        ]
        read_only_fields = ["id", "is_published"]
        extra_kwargs = {
            "description": {"required": False},
            "price": {"required": False, "allow_null": True},
            "stock_quantity": {"required": False, "allow_null": True},
        }

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_stock_quantity(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
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

        return attrs

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        product = Product.objects.create(**validated_data)
        for position, image in enumerate(images):
            ProductImage.objects.create(product=product, image=image, position=position)
        return product

    def update(self, instance, validated_data):
        images = validated_data.pop("images", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if images is not None:
            instance.images.all().delete()
            for position, image in enumerate(images):
                ProductImage.objects.create(product=instance, image=image, position=position)
        return instance


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
