from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product
from apps.orders.models import Order, OrderDelivery, OrderItem, OrderItemStatusEvent
from apps.payments.models import PaymentRecord
from apps.payments.services import MOBILE_MONEY_METHOD, mobile_money_enabled, normalise_msisdn
from apps.vendors.models import Shop

COORDINATE_PLACES = Decimal("0.000001")


class DeliveryPinSerializer(serializers.Serializer):
    """The customer's delivery pin (007-delivery-fee). Accepts any float precision a device's GPS
    reports and rounds to the 6 decimal places (~0.1 m) the database stores."""

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for key in ("latitude", "longitude"):
            attrs[key] = Decimal(str(attrs[key])).quantize(COORDINATE_PLACES)
        return attrs


class ShippingSerializer(DeliveryPinSerializer):
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
    # Mobile money only: the number the payment prompt is pushed to, and its network.
    msisdn = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.ChoiceField(
        choices=PaymentRecord.Provider.choices, required=False, allow_blank=True
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs["payment_method"] != MOBILE_MONEY_METHOD or not mobile_money_enabled():
            attrs.pop("msisdn", None)
            attrs.pop("provider", None)
            return attrs

        errors = {}
        msisdn = normalise_msisdn(attrs.get("msisdn", ""))
        if msisdn is None:
            errors["msisdn"] = ["Enter a Tanzanian mobile number, e.g. 0712345678."]
        if not attrs.get("provider"):
            errors["provider"] = ["Choose your mobile money network."]
        if errors:
            raise serializers.ValidationError(errors)
        attrs["msisdn"] = msisdn
        return attrs


def rider_brief(rider):
    """`{id, name, phone}` for a line's assigned rider, or None. Phone comes from the rider's
    `RiderProfile` (apps.delivery), so callers should `select_related("rider__rider_profile")`."""

    if rider is None:
        return None
    profile = getattr(rider, "rider_profile", None)
    return {"id": rider.id, "name": rider.name, "phone": profile.phone if profile else ""}


class RiderBriefMixin(serializers.Serializer):
    rider = serializers.SerializerMethodField()

    def get_rider(self, obj):
        return rider_brief(obj.rider)


class OrderItemProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name"]
        read_only_fields = fields


class OrderItemSerializer(RiderBriefMixin, serializers.ModelSerializer):
    product = OrderItemProductSerializer(read_only=True)
    shop_name = serializers.CharField(source="product.shop.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "shop_name",
            "quantity",
            "unit_price",
            "subtotal",
            "status",
            "rider",
        ]
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
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)


class VendorOrderItemSerializer(RiderBriefMixin, serializers.ModelSerializer):
    """A Vendor's own fulfillment queue row — current status only, no history (Administrator-only,
    Clarifications session 2026-09-21)."""

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    product = OrderItemProductSerializer(read_only=True)
    shipping = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "product",
            "quantity",
            "unit_price",
            "commission_rate",
            "commission_amount",
            "vendor_earning",
            "payout_id",
            "status",
            "shipping",
            "rider",
        ]
        read_only_fields = fields

    def get_shipping(self, obj):
        return VendorOrderItemShippingSerializer(obj.order).data


class OrderItemStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemStatusEvent
        fields = ["status", "changed_at"]
        read_only_fields = fields


class AdminOrderItemShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name"]
        read_only_fields = fields


class AdminOrderItemSerializer(RiderBriefMixin, serializers.ModelSerializer):
    """Administrator oversight row — the only response shape that ever includes
    `status_history` (Clarifications session 2026-09-21)."""

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    product = OrderItemProductSerializer(read_only=True)
    shop = AdminOrderItemShopSerializer(source="product.shop", read_only=True)
    status_history = OrderItemStatusEventSerializer(
        source="status_events", many=True, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "product",
            "shop",
            "quantity",
            "unit_price",
            "commission_rate",
            "commission_amount",
            "vendor_earning",
            "payout_id",
            "status",
            "status_history",
            "rider",
        ]
        read_only_fields = fields


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


class AssignRiderSerializer(serializers.Serializer):
    rider_id = serializers.IntegerField(allow_null=True)


class PaymentRecordSerializer(serializers.ModelSerializer):
    msisdn = serializers.CharField(source="masked_msisdn", read_only=True)

    class Meta:
        model = PaymentRecord
        fields = ["method", "status", "amount", "provider", "msisdn", "failure_reason"]
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
            "latitude",
            "longitude",
        ]
        read_only_fields = fields


def money(value):
    return str(Decimal(value).quantize(Decimal("0.01")))


class OrderTotalsMixin(serializers.Serializer):
    """`items_subtotal`, `delivery_fee` and `total` (= items + delivery) for an `Order`."""

    items_subtotal = serializers.SerializerMethodField()
    delivery_fee = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def get_items_subtotal(self, obj):
        return money(obj.items_subtotal)

    def get_delivery_fee(self, obj):
        return money(obj.delivery_fee)

    def get_total(self, obj):
        return money(obj.total)


class OrderDeliverySerializer(serializers.ModelSerializer):
    shop_id = serializers.IntegerField(source="shop.id", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model = OrderDelivery
        fields = ["shop_id", "shop_name", "distance_km", "fee"]
        read_only_fields = fields


class OrderSerializer(OrderTotalsMixin, serializers.ModelSerializer):
    """List shape (`GET /api/orders/`) — summary only, no line items or shipping (User Story 4)."""

    class Meta:
        model = Order
        fields = ["id", "placed_at", "status", "items_subtotal", "delivery_fee", "total"]
        read_only_fields = fields


class OrderDetailSerializer(OrderTotalsMixin, serializers.ModelSerializer):
    """Detail shape shared by `POST /api/checkout/`'s `201` response and
    `GET /api/orders/{id}/` (contracts/cart-checkout-api.md)."""

    shipping = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    deliveries = OrderDeliverySerializer(many=True, read_only=True)
    payment = PaymentRecordSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "placed_at",
            "status",
            "items_subtotal",
            "delivery_fee",
            "total",
            "shipping",
            "items",
            "deliveries",
            "payment",
        ]
        read_only_fields = fields

    def get_shipping(self, obj):
        return OrderShippingSerializer(obj).data
