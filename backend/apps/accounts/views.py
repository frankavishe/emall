"""Shared token-issuance plumbing (task T014).

Not a routed endpoint on its own — reused by the register/login/refresh views built in later
phases. Access tokens go in the JSON response body only (held in memory on the frontend); refresh
tokens are set *exclusively* as an httpOnly/Secure/SameSite cookie, never in a JSON body
(Constitution Principle III, research.md §1).
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator
from apps.orders.models import Order, OrderItem
from apps.vendors.models import Shop
from apps.vendors.serializers import ShopBriefSerializer

from .models import EmailVerificationToken, PasswordResetToken, User
from .serializers import (
    AdminCustomerSerializer,
    AdminCustomerUpdateSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterCustomerSerializer,
    RegisterVendorSerializer,
    UserProfileSerializer,
    VerifyEmailConfirmSerializer,
)
from .services import (
    blacklist_all_tokens,
    check_otp,
    issue_password_reset_token,
    issue_verification_token,
)


BLOCKED_ACCOUNT_DETAIL = "This account has been blocked. Contact support."


class TokenResponseMixin:
    """Issues a simplejwt access/refresh pair and puts each half where it belongs."""

    def issue_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        return access, str(refresh)

    def set_refresh_cookie(self, response, refresh_token):
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )

    def clear_refresh_cookie(self, response):
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )

    def get_refresh_token_from_cookie(self, request):
        return request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)


class RegisterCustomerView(TokenResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()

        try:
            issue_verification_token(user)
        except Exception:
            pass

        access, refresh = self.issue_tokens(user)
        response = Response(
            {"access": access, "user": UserProfileSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
        self.set_refresh_cookie(response, refresh)
        return response


class RegisterVendorView(TokenResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterVendorSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        # An existing customer account adding a shop is an upgrade, not a new account.
        upgraded = serializer.existing_user is not None
        with transaction.atomic():
            user, shop = serializer.save()

        if not user.is_email_verified:
            try:
                issue_verification_token(user)
            except Exception:
                pass

        access, refresh = self.issue_tokens(user)
        response = Response(
            {
                "access": access,
                "user": UserProfileSerializer(user).data,
                "shops": ShopBriefSerializer(
                    user.shops.all(), many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK if upgraded else status.HTTP_201_CREATED,
        )
        self.set_refresh_cookie(response, refresh)
        return response


class LoginView(TokenResponseMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            # ModelBackend refuses inactive accounts. Only someone who knows the password learns
            # the account is blocked; everyone else gets the same generic message.
            blocked = User.objects.filter(email=email, is_active=False).first()
            if blocked is not None and blocked.check_password(password):
                return Response(
                    {"detail": BLOCKED_ACCOUNT_DETAIL}, status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED
            )

        access, refresh = self.issue_tokens(user)
        response = Response(
            {"access": access, "user": UserProfileSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        self.set_refresh_cookie(response, refresh)
        return response


class LogoutView(TokenResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = self.get_refresh_token_from_cookie(request)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        self.clear_refresh_cookie(response)
        return response


class RefreshView(TokenResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = self.get_refresh_token_from_cookie(request)
        if not raw_refresh:
            return Response(
                {"detail": "Refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        data = serializer.validated_data

        response = Response({"access": data["access"]}, status=status.HTTP_200_OK)
        self.set_refresh_cookie(response, data.get("refresh", raw_refresh))
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserProfileSerializer(request.user).data
        if request.user.has_role(User.Role.VENDOR):
            data["shops"] = ShopBriefSerializer(
                request.user.shops.all(), many=True, context={"request": request}
            ).data
        return Response(data)


class VerifyEmailRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        if not request.user.is_email_verified:
            issue_verification_token(request.user)
        return Response(status=status.HTTP_202_ACCEPTED)


INVALID_CODE_DETAIL = "This code is invalid or has expired."


class VerifyEmailConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_confirm"

    def post(self, request):
        serializer = VerifyEmailConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"]

        user = User.objects.filter(email=email).first()
        if user is not None and user.is_email_verified:
            return Response({"detail": "Email already verified."}, status=status.HTTP_200_OK)

        if user is None or not check_otp(EmailVerificationToken, user, code):
            return Response({"detail": INVALID_CODE_DETAIL}, status=status.HTTP_400_BAD_REQUEST)

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email=email).first()
        if user is not None:
            issue_password_reset_token(user)

        return Response(
            {"detail": "If that email is registered, a reset code has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(email=email).first()
        if user is None or not check_otp(PasswordResetToken, user, code):
            return Response({"detail": INVALID_CODE_DETAIL}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])

            blacklist_all_tokens(user)

        return Response(
            {"detail": "Password updated. Please log in again."}, status=status.HTTP_200_OK
        )


def _customers():
    """Shopper accounts (vendors included — they're customers with `is_vendor`); never
    administrators or riders. Totals use subqueries so the order and shop joins can't multiply
    each other's rows."""
    money = DecimalField(max_digits=12, decimal_places=2)
    spent = (
        OrderItem.objects.filter(order__customer=OuterRef("pk"))
        .values("order__customer")
        .annotate(total=Sum(F("unit_price") * F("quantity"), output_field=money))
        .values("total")
    )
    shops = (
        Shop.objects.filter(owner=OuterRef("pk"))
        .values("owner")
        .annotate(count=Count("id"))
        .values("count")
    )
    return User.objects.filter(role=User.Role.CUSTOMER).annotate(
        order_count=Count("orders", distinct=True),
        total_spent=Coalesce(Subquery(spent, output_field=money), Value(0, output_field=money)),
        shop_count=Coalesce(Subquery(shops), Value(0)),
    )


def _recent_orders(user, limit=5):
    orders = (
        Order.objects.filter(customer=user)
        .annotate(
            item_count=Count("items"),
            order_total=Sum(
                F("items__unit_price") * F("items__quantity"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        .order_by("-placed_at")[:limit]
    )
    return [
        {
            "id": order.id,
            "placed_at": order.placed_at,
            "item_count": order.item_count,
            "total": f"{order.order_total or 0:.2f}",
        }
        for order in orders
    ]


class AdminCustomerListView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminCustomerSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = _customers().order_by("-date_joined", "-id")
        params = self.request.query_params
        q = params.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(email__icontains=q))
        is_active = params.get("is_active")
        if is_active in ("true", "false"):
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset


class AdminCustomerDetailView(APIView):
    """Scoped to customer accounts, so an administrator or rider ID 404s here — riders are
    deactivated from the riders screen, and admins can't block each other."""

    permission_classes = [IsAdministrator]

    def _response(self, customer_id):
        customer = get_object_or_404(_customers(), pk=customer_id)
        data = AdminCustomerSerializer(customer).data
        data["recent_orders"] = _recent_orders(customer)
        return Response(data)

    def get(self, request, customer_id):
        return self._response(customer_id)

    def patch(self, request, customer_id):
        customer = get_object_or_404(User, pk=customer_id, role=User.Role.CUSTOMER)
        serializer = AdminCustomerUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_active = serializer.validated_data["is_active"]

        with transaction.atomic():
            if customer.is_active != is_active:
                customer.is_active = is_active
                customer.save(update_fields=["is_active"])
            # Blocking logs the customer out of every device.
            if not is_active:
                blacklist_all_tokens(customer)

        return self._response(customer_id)
