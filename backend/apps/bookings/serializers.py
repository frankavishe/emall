from collections import defaultdict

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.bookings.models import Booking, BookingStatusEvent, OpeningHours, Service, ShopClosure
from apps.bookings.permissions import require_bookable_shop
from apps.bookings.slots import market_today, market_zone
from apps.catalog.models import Category
from apps.catalog.serializers import CatalogShopSerializer
from apps.core.validators import PHONE_REGEX
from apps.vendors.models import Shop

MAX_BOOKING_CAPACITY = 1000


class PublicServiceSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    shop = CatalogShopSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "price",
            "duration_minutes",
            "category",
            "category_slug",
            "shop",
        ]
        read_only_fields = fields


class VendorServiceShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "status"]
        read_only_fields = fields


class VendorServiceSerializer(serializers.ModelSerializer):
    shop = VendorServiceShopSerializer(read_only=True)
    category = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "shop",
            "name",
            "description",
            "price",
            "duration_minutes",
            "category",
            "category_name",
            "is_published",
        ]
        read_only_fields = fields


class VendorServiceWriteSerializer(serializers.ModelSerializer):
    """`shop_id` is required on create and ignored on update: a service never changes shop."""

    shop_id = serializers.PrimaryKeyRelatedField(
        source="shop", queryset=Shop.objects.all(), write_only=True, required=False
    )
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.filter(kind=Category.Kind.SERVICE)
    )

    class Meta:
        model = Service
        fields = ["shop_id", "name", "description", "price", "duration_minutes", "category"]
        # The partial unique constraint is checked in `validate`, against the right shop.
        validators = []

    def validate_category(self, value):
        if value.children.exists():
            raise serializers.ValidationError(f"Choose a subcategory of {value.name}.")
        return value

    def validate_duration_minutes(self, value):
        step = settings.BOOKING_SLOT_MINUTES
        if value % step != 0:
            raise serializers.ValidationError(f"Duration must be a multiple of {step} minutes.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            shop = attrs.get("shop")
            if shop is None:
                raise serializers.ValidationError({"shop_id": "This field is required."})
            if shop.owner_id != self.context["request"].user.id:
                raise PermissionDenied("You can only add services to a shop you own.")
            require_bookable_shop(shop)
        else:
            attrs.pop("shop", None)
            shop = self.instance.shop

        name = attrs.get("name")
        if name:
            duplicates = Service.objects.filter(shop=shop, name=name, is_archived=False)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": "A service with this name already exists in this shop."}
                )
        return attrs


class OpeningPeriodSerializer(serializers.ModelSerializer):
    opens_at = serializers.TimeField(format="%H:%M")
    closes_at = serializers.TimeField(format="%H:%M")

    class Meta:
        model = OpeningHours
        fields = ["weekday", "opens_at", "closes_at"]
        # Checked here so an invalid period is a 400, not a database error.
        validators = []

    def validate(self, attrs):
        if attrs["closes_at"] <= attrs["opens_at"]:
            raise serializers.ValidationError(
                {"closes_at": "A period must close after it opens, on the same day."}
            )
        return attrs


class ShopScheduleSerializer(serializers.Serializer):
    booking_capacity = serializers.IntegerField(min_value=1, max_value=MAX_BOOKING_CAPACITY)
    hours = OpeningPeriodSerializer(many=True)

    def validate_hours(self, value):
        by_day = defaultdict(list)
        for period in value:
            by_day[period["weekday"]].append(period)
        for periods in by_day.values():
            periods.sort(key=lambda period: period["opens_at"])
            for earlier, later in zip(periods, periods[1:], strict=False):
                if later["opens_at"] < earlier["closes_at"]:
                    raise serializers.ValidationError(
                        "Opening periods on the same day can't overlap."
                    )
        return value


class ShopClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopClosure
        fields = ["id", "date", "note"]
        read_only_fields = ["id"]

    def validate_date(self, value):
        if value < market_today():
            raise serializers.ValidationError("Choose today or a future date.")
        if ShopClosure.objects.filter(shop=self.context["shop"], date=value).exists():
            raise serializers.ValidationError("This date is already marked as closed.")
        return value


class MarketDateTimeField(serializers.DateTimeField):
    """Booking times go out with the market's `+03:00` offset, as open times do."""

    def __init__(self, **kwargs):
        kwargs.setdefault("default_timezone", market_zone())
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)


class BookingRequestSerializer(serializers.Serializer):
    service = serializers.IntegerField(min_value=1)
    starts_at = serializers.DateTimeField()
    contact_phone = serializers.RegexField(
        PHONE_REGEX, error_messages={"invalid": "Enter a valid phone number."}
    )
    customer_note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )


class BookingReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)


class BookingServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "duration_minutes"]
        read_only_fields = fields


class BookingShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name"]
        read_only_fields = fields


class BookingHistorySerializer(serializers.ModelSerializer):
    created_at = MarketDateTimeField()

    class Meta:
        model = BookingStatusEvent
        fields = ["status", "reason", "created_at"]
        read_only_fields = fields


class AdminBookingHistorySerializer(BookingHistorySerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta(BookingHistorySerializer.Meta):
        fields = [*BookingHistorySerializer.Meta.fields, "actor_email"]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    """What the customer sees. Providers and Administrators add to it below."""

    service = BookingServiceSerializer(read_only=True)
    shop = BookingShopSerializer(read_only=True)
    starts_at = MarketDateTimeField()
    ends_at = MarketDateTimeField()
    respond_by = MarketDateTimeField()
    pay_by = MarketDateTimeField()
    created_at = MarketDateTimeField()
    accepted_at = MarketDateTimeField()
    confirmed_at = MarketDateTimeField()
    completed_at = MarketDateTimeField()
    cancelled_at = MarketDateTimeField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "status",
            "service",
            "shop",
            "starts_at",
            "ends_at",
            "respond_by",
            "pay_by",
            "contact_phone",
            "customer_note",
            "status_reason",
            "price",
            "created_at",
            "accepted_at",
            "confirmed_at",
            "completed_at",
            "cancelled_at",
        ]
        read_only_fields = fields


class BookingDetailSerializer(BookingSerializer):
    history = BookingHistorySerializer(source="status_events", many=True, read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = [*BookingSerializer.Meta.fields, "history"]
        read_only_fields = fields


class VendorBookingSerializer(BookingSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = [
            *BookingSerializer.Meta.fields,
            "customer_name",
            "commission_amount",
            "vendor_earning",
        ]
        read_only_fields = fields


class VendorBookingDetailSerializer(VendorBookingSerializer):
    history = BookingHistorySerializer(source="status_events", many=True, read_only=True)

    class Meta(VendorBookingSerializer.Meta):
        fields = [*VendorBookingSerializer.Meta.fields, "history"]
        read_only_fields = fields


class BookingCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()


class AdminBookingSerializer(BookingSerializer):
    customer = BookingCustomerSerializer(read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = [
            *BookingSerializer.Meta.fields,
            "customer",
            "commission_rate",
            "commission_amount",
            "vendor_earning",
        ]
        read_only_fields = fields


class AdminBookingDetailSerializer(AdminBookingSerializer):
    history = AdminBookingHistorySerializer(source="status_events", many=True, read_only=True)

    class Meta(AdminBookingSerializer.Meta):
        fields = [*AdminBookingSerializer.Meta.fields, "history"]
        read_only_fields = fields


class ClosureBookingSerializer(BookingSerializer):
    """An active booking on a date the provider just closed, as a warning."""

    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = ["id", "status", "service", "starts_at", "customer_name"]
        read_only_fields = fields
