from decimal import Decimal

from rest_framework import serializers

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product
from apps.vendors.models import Shop


class CartItemProductSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "shop_name"]
        read_only_fields = fields


class CartItemSerializer(serializers.ModelSerializer):
    """Read shape for a cart line. `unit_price`/`subtotal`/`is_available`/`unavailable_reason`
    are all read live from the current `Product` via CartItem's properties (research.md §2,
    data-model.md), never a stored/frozen value."""

    product = CartItemProductSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    unavailable_reason = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "quantity",
            "unit_price",
            "subtotal",
            "is_available",
            "unavailable_reason",
        ]
        read_only_fields = fields


class CartSerializer(serializers.ModelSerializer):
    """`total` sums only *available* lines' subtotals (data-model.md, User Story 3) — an
    unavailable line is still returned so the Customer can see and resolve it, but never
    contributes to the total."""

    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total"]
        read_only_fields = fields

    def get_total(self, obj):
        total = sum(
            (item.subtotal for item in obj.items.all() if item.is_available),
            Decimal("0.00"),
        )
        return str(total.quantize(Decimal("0.01")))


class CartItemCreateSerializer(serializers.Serializer):
    """Validates a single add-to-cart request in isolation (FR-001, FR-007). Merging into an
    already-present line and re-checking the *combined* quantity against stock (FR-005,
    research.md §3) is handled by the view, which alone knows whether a line already exists."""

    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(is_published=True),
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_id(self, product):
        if product.shop.status != Shop.Status.APPROVED:
            raise serializers.ValidationError("This product is not available.")
        return product

    def validate(self, attrs):
        product = attrs["product"]
        quantity = attrs["quantity"]
        available = product.stock_quantity or 0
        if quantity > available:
            raise serializers.ValidationError({"quantity": f"Only {available} available."})
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """Validates a quantity change on an existing line (FR-003, FR-007)."""

    class Meta:
        model = CartItem
        fields = ["quantity"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        available = self.instance.product.stock_quantity or 0
        if value > available:
            raise serializers.ValidationError(f"Only {available} available.")
        return value
