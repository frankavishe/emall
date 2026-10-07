from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product
from apps.finance.models import Payout, PlatformSettings
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from apps.vendors.serializers import ShopLogoUrlMixin

_MONEY = {"max_digits": 14, "decimal_places": 2, "read_only": True}
_RATE = {"max_digits": 5, "decimal_places": 2}


class BalanceFiguresSerializer(serializers.Serializer):
    gross_sales = serializers.DecimalField(**_MONEY)
    commission_earned = serializers.DecimalField(**_MONEY)
    commission_pending = serializers.DecimalField(**_MONEY)
    pending_earnings = serializers.DecimalField(**_MONEY)
    available_balance = serializers.DecimalField(**_MONEY)
    in_payout = serializers.DecimalField(**_MONEY)
    paid_out = serializers.DecimalField(**_MONEY)


class PlatformSummarySerializer(BalanceFiguresSerializer):
    order_count = serializers.IntegerField(read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    default_commission_rate = serializers.DecimalField(**_RATE, read_only=True)


class DateRangeSerializer(serializers.Serializer):
    # `from` is a Python keyword, so it's mapped in the view.
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class PlatformSettingsSerializer(serializers.ModelSerializer):
    default_commission_rate = serializers.DecimalField(
        **_RATE, min_value=Decimal("0"), max_value=Decimal("100")
    )

    class Meta:
        model = PlatformSettings
        fields = ["default_commission_rate", "updated_at"]
        read_only_fields = ["updated_at"]


class ShopCommissionSerializer(serializers.Serializer):
    commission_rate = serializers.DecimalField(
        **_RATE, min_value=Decimal("0"), max_value=Decimal("100"), allow_null=True
    )


class PayoutDetailsSerializer(serializers.ModelSerializer):
    """The shop owner's mobile-money destination. All three fields are required together."""

    payout_network = serializers.ChoiceField(choices=Shop.PayoutNetwork.choices)
    payout_phone = serializers.RegexField(
        r"^\+?[0-9]{9,15}$", error_messages={"invalid": "Enter a valid phone number."}
    )
    payout_account_name = serializers.CharField(max_length=255)

    class Meta:
        model = Shop
        fields = ["payout_network", "payout_phone", "payout_account_name"]


class AdminShopBalanceSerializer(ShopLogoUrlMixin, BalanceFiguresSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    commission_rate = serializers.SerializerMethodField()
    commission_rate_override = serializers.DecimalField(
        source="commission_rate", **_RATE, read_only=True
    )
    has_payout_details = serializers.BooleanField(read_only=True)

    def get_commission_rate(self, obj):
        rate = obj.commission_rate
        if rate is None:
            rate = self.context["default_commission_rate"]
        return str(rate)


class AdminShopDetailSerializer(ShopLogoUrlMixin, serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)
    published_product_count = serializers.IntegerField(read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "status",
            "status_reason",
            "created_at",
            "status_changed_at",
            "logo_url",
            "owner",
            "commission_rate",
            "payout_network",
            "payout_phone",
            "payout_account_name",
            "product_count",
            "published_product_count",
            "balance",
        ]
        read_only_fields = fields

    def get_owner(self, obj):
        return {"id": obj.owner.id, "name": obj.owner.name, "email": obj.owner.email}

    def get_balance(self, obj):
        figures = self.context["balance"]
        data = BalanceFiguresSerializer(figures).data
        data["commission_rate"] = str(figures["commission_rate"])
        data["commission_rate_is_override"] = figures["commission_rate_is_override"]
        return data


class PayoutSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", default=None)
    line_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Payout
        fields = [
            "id",
            "reference",
            "shop",
            "amount",
            "status",
            "network",
            "phone",
            "account_name",
            "provider_reference",
            "failure_reason",
            "created_by_name",
            "created_at",
            "completed_at",
            "line_count",
        ]
        read_only_fields = fields

    def get_shop(self, obj):
        return {"id": obj.shop_id, "name": obj.shop.name}


class PayoutLineSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "product_name",
            "quantity",
            "unit_price",
            "subtotal",
            "commission_rate",
            "commission_amount",
            "vendor_earning",
            "status",
        ]
        read_only_fields = fields


class PayoutDetailSerializer(PayoutSerializer):
    items = PayoutLineSerializer(many=True, read_only=True)

    class Meta(PayoutSerializer.Meta):
        fields = PayoutSerializer.Meta.fields + ["items"]
        read_only_fields = fields


class AdminTransactionSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(read_only=True)
    customer = serializers.SerializerMethodField()
    commission_total = serializers.DecimalField(**_MONEY)
    shop_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PaymentRecord
        fields = [
            "id",
            "order_id",
            "customer",
            "amount",
            "method",
            "status",
            "transaction_reference",
            "created_at",
            "commission_total",
            "shop_count",
        ]
        read_only_fields = fields

    def get_customer(self, obj):
        customer = obj.order.customer
        return {"id": customer.id, "name": customer.name, "email": customer.email}


class AdminOrderLineSerializer(PayoutLineSerializer):
    shop = serializers.SerializerMethodField()
    payout = serializers.SerializerMethodField()

    class Meta(PayoutLineSerializer.Meta):
        fields = PayoutLineSerializer.Meta.fields + ["shop", "payout"]
        read_only_fields = fields

    def get_shop(self, obj):
        return {"id": obj.product.shop_id, "name": obj.product.shop.name}

    def get_payout(self, obj):
        if obj.payout is None:
            return None
        return {"id": obj.payout.id, "status": obj.payout.status}


class AdminOrderDetailSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    items = AdminOrderLineSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    commission_total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "placed_at",
            "status",
            "customer",
            "recipient_name",
            "address_line",
            "city",
            "region",
            "postal_code",
            "country",
            "phone",
            "total",
            "commission_total",
            "payment",
            "items",
        ]
        read_only_fields = fields

    def get_customer(self, obj):
        return {"id": obj.customer.id, "name": obj.customer.name, "email": obj.customer.email}

    def get_payment(self, obj):
        payment = getattr(obj, "payment", None)
        if payment is None:
            return None
        return {
            "method": payment.method,
            "status": payment.status,
            "amount": str(payment.amount),
            "transaction_reference": payment.transaction_reference,
            "created_at": payment.created_at,
        }

    def get_total(self, obj):
        return str(sum((item.subtotal for item in obj.items.all()), Decimal("0.00")))

    def get_commission_total(self, obj):
        return str(sum((item.commission_amount for item in obj.items.all()), Decimal("0.00")))


class AdminProductSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField()
    category = serializers.CharField(source="category.name", default=None)
    units_sold = serializers.IntegerField(read_only=True)
    revenue = serializers.DecimalField(**_MONEY)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "shop",
            "category",
            "price",
            "stock_quantity",
            "is_published",
            "is_deleted",
            "created_at",
            "units_sold",
            "revenue",
        ]
        read_only_fields = fields

    def get_shop(self, obj):
        return {"id": obj.shop_id, "name": obj.shop.name, "status": obj.shop.status}


class VendorShopEarningsSerializer(BalanceFiguresSerializer):
    shop_id = serializers.IntegerField(read_only=True)
    shop_name = serializers.CharField(read_only=True)
    commission_rate = serializers.DecimalField(**_RATE, read_only=True)
    has_payout_details = serializers.BooleanField(read_only=True)
    payout_network = serializers.CharField(read_only=True)
    payout_phone = serializers.CharField(read_only=True)
    payout_account_name = serializers.CharField(read_only=True)
