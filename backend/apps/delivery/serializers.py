from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.delivery.models import RiderProfile
from apps.orders.models import OrderItem
from apps.orders.serializers import OrderItemProductSerializer, VendorOrderItemShippingSerializer

ACTIVE_DELIVERY_STATUSES = [OrderItem.Status.PROCESSING, OrderItem.Status.SHIPPED]


class AdminRiderSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="rider_profile.phone", read_only=True)
    vehicle_type = serializers.CharField(source="rider_profile.vehicle_type", read_only=True)
    plate_number = serializers.CharField(source="rider_profile.plate_number", read_only=True)
    active_delivery_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "is_active",
            "phone",
            "vehicle_type",
            "plate_number",
            "active_delivery_count",
            "date_joined",
        ]
        read_only_fields = fields

    def get_active_delivery_count(self, obj):
        annotated = getattr(obj, "active_delivery_count", None)
        if annotated is not None:
            return annotated
        return obj.deliveries.filter(status__in=ACTIVE_DELIVERY_STATUSES).count()


class AdminRiderCreateSerializer(serializers.Serializer):
    """An admin registers a rider with a temporary password they hand over in person. The
    email counts as verified — the admin vetted the rider."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    phone = serializers.CharField(max_length=32)
    vehicle_type = serializers.ChoiceField(choices=RiderProfile.VehicleType.choices)
    plate_number = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        profile_data = {
            "phone": validated_data.pop("phone"),
            "vehicle_type": validated_data.pop("vehicle_type"),
            "plate_number": validated_data.pop("plate_number", ""),
        }
        with transaction.atomic():
            user = User.objects.create_user(
                role=User.Role.RIDER, is_email_verified=True, **validated_data
            )
            RiderProfile.objects.create(user=user, **profile_data)
        return user


class AdminRiderUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    phone = serializers.CharField(max_length=32, required=False)
    vehicle_type = serializers.ChoiceField(
        choices=RiderProfile.VehicleType.choices, required=False
    )
    plate_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    def validate_password(self, value):
        validate_password(value)
        return value

    def update(self, user, validated_data):
        user_fields = []
        for field in ("name", "is_active"):
            if field in validated_data:
                setattr(user, field, validated_data[field])
                user_fields.append(field)
        if "password" in validated_data:
            user.set_password(validated_data["password"])
            user_fields.append("password")

        profile = user.rider_profile
        profile_fields = []
        for field in ("phone", "vehicle_type", "plate_number"):
            if field in validated_data:
                setattr(profile, field, validated_data[field])
                profile_fields.append(field)

        with transaction.atomic():
            if user_fields:
                user.save(update_fields=user_fields)
            if profile_fields:
                profile.save(update_fields=profile_fields)
        return user


class RiderDeliverySerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    product = OrderItemProductSerializer(read_only=True)
    pickup = serializers.SerializerMethodField()
    dropoff = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "product",
            "quantity",
            "status",
            "pickup",
            "dropoff",
            "rider_assigned_at",
        ]
        read_only_fields = fields

    def get_pickup(self, obj):
        return {"shop_name": obj.product.shop.name}

    def get_dropoff(self, obj):
        return VendorOrderItemShippingSerializer(obj.order).data


class RiderDeliveryStatusSerializer(serializers.Serializer):
    """A rider can only mark a line picked up (SHIPPED) or delivered — never cancel it."""

    status = serializers.ChoiceField(
        choices=[OrderItem.Status.SHIPPED, OrderItem.Status.DELIVERED]
    )
