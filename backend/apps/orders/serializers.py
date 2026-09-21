from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem, OrderItemStatusEvent
from apps.payments.models import PaymentRecord


class ShippingSerializer(serializers.Serializer):
    recipient_name = serializers.CharField()
    address_line = serializers.CharField()
    city = serializers.CharField()
    region = serializers.CharField()
    postal_code = serializers.CharField()
    country = serializers.CharField()
    phone = serializers.CharField()


class CheckoutSerializer(serializers.Serializer):
    """Request shape only (contracts/cart-checkout-api.md) — the view passes
    `validated_data` straight through to `orders.services.place_order()`."""

    shipping = ShippingSerializer()
    payment_method = serializers.CharField()


class OrderItemProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name"]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderItemProductSerializer(read_only=True)
    shop_name = serializers.CharField(source="product.shop.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "shop_name", "quantity", "unit_price", "subtotal", "status"]
        read_only_fields = fields


class VendorOrderItemShippingSerializer(serializers.Serializer):
    """Denormalized from `order_item.order` — a Vendor needs shipping details to fulfill a line
    without a second request (contracts/order-fulfillment-api.md)."""

    recipient_name = serializers.CharField()
    address_line = serializers.CharField()
    city = serializers.CharField()
    region = serializers.CharField()
    postal_code = serializers.CharField()
    country = serializers.CharField()
    phone = serializers.CharField()


class VendorOrderItemSerializer(serializers.ModelSerializer):
    """A Vendor's own fulfillment queue row — current status only, no history (Administrator-only,
    Clarifications session 2026-09-21)."""

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    product = OrderItemProductSerializer(read_only=True)
    shipping = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "order_id", "product", "quantity", "unit_price", "status", "shipping"]
        read_only_fields = fields

    def get_shipping(self, obj):
        return VendorOrderItemShippingSerializer(obj.order).data


class OrderItemStatusUpdateSerializer(serializers.Serializer):
    """Request shape only (contracts/order-fulfillment-api.md) — a Vendor can never request
    `PENDING`, since that's only ever set by `place_order()`."""

    status = serializers.ChoiceField(
        choices=[
            OrderItem.Status.PROCESSING,
            OrderItem.Status.SHIPPED,
            OrderItem.Status.DELIVERED,
            OrderItem.Status.CANCELLED,
        ]
    )


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = ["method", "status"]
        read_only_fields = fields


class OrderShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "recipient_name",
            "address_line",
            "city",
            "region",
            "postal_code",
            "country",
            "phone",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """List shape (`GET /api/orders/`) — summary only, no line items or shipping (User Story 4)."""

    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "placed_at", "status", "total"]
        read_only_fields = fields

    def get_total(self, obj):
        total = sum((item.subtotal for item in obj.items.all()), Decimal("0.00"))
        return str(total.quantize(Decimal("0.01")))


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detail shape shared by `POST /api/checkout/`'s `201` response and
    `GET /api/orders/{id}/` (contracts/cart-checkout-api.md)."""

    total = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentRecordSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "placed_at", "status", "total", "shipping", "items", "payment"]
        read_only_fields = fields

    def get_total(self, obj):
        total = sum((item.subtotal for item in obj.items.all()), Decimal("0.00"))
        return str(total.quantize(Decimal("0.01")))

    def get_shipping(self, obj):
        return OrderShippingSerializer(obj).data
