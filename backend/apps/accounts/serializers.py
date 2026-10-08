from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User
from apps.vendors.models import Shop


class UserProfileSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "roles", "is_email_verified"]
        read_only_fields = fields


class RegisterCustomerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists — log in instead."
            )
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.CUSTOMER, **validated_data)


class RegisterVendorSerializer(serializers.Serializer):
    """Registers a vendor. If the email already belongs to a customer account, the matching
    password turns that same account into a vendor too (one email, both roles) instead of
    rejecting it. `self.existing_user` is set when that upgrade path applies."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    shop_name = serializers.CharField(max_length=255)

    existing_user = None

    def validate_email(self, value):
        return value.strip().lower()

    def validate_shop_name(self, value):
        if Shop.objects.filter(name=value).exists():
            raise serializers.ValidationError("A shop with this name already exists.")
        return value

    def validate(self, attrs):
        user = User.objects.filter(email=attrs["email"]).first()
        if user is None:
            try:
                validate_password(attrs["password"])
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
            return attrs

        if user.role in (User.Role.ADMINISTRATOR, User.Role.RIDER):
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )
        if user.is_vendor:
            raise serializers.ValidationError(
                {
                    "email": "This account is already a vendor — log in and request another "
                    "shop from your account page."
                }
            )
        authenticated = authenticate(
            self.context.get("request"), username=attrs["email"], password=attrs["password"]
        )
        if authenticated is None or authenticated.pk != user.pk:
            raise serializers.ValidationError(
                {
                    "email": "An account with this email already exists. Enter that account's "
                    "password to add a shop to it."
                }
            )
        self.existing_user = user
        return attrs

    def create(self, validated_data):
        shop_name = validated_data.pop("shop_name")
        if self.existing_user is not None:
            user = self.existing_user
            user.is_vendor = True
            user.save(update_fields=["is_vendor"])
        else:
            user = User.objects.create_user(
                role=User.Role.CUSTOMER, is_vendor=True, **validated_data
            )
        shop = Shop.objects.create(owner=user, name=shop_name)
        return user, shop


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class VerifyEmailConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the 6-digit code."})


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the 6-digit code."})
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class AdminCustomerSerializer(serializers.ModelSerializer):
    """Administrator view of a shopper account. `order_count`, `total_spent` and `shop_count`
    come from annotations on the admin customer queryset (accounts.views._customers)."""

    order_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    shop_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "is_vendor",
            "is_email_verified",
            "is_active",
            "date_joined",
            "order_count",
            "total_spent",
            "shop_count",
        ]
        read_only_fields = fields


class AdminCustomerUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
