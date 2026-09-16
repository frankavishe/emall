"""Shared token-issuance plumbing (task T014).

Not a routed endpoint on its own — reused by the register/login/refresh views built in later
phases. Access tokens go in the JSON response body only (held in memory on the frontend); refresh
tokens are set *exclusively* as an httpOnly/Secure/SameSite cookie, never in a JSON body
(Constitution Principle III, research.md §1).
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.vendors.serializers import ShopBriefSerializer

from .models import EmailVerificationToken, PasswordResetToken, User
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterCustomerSerializer,
    RegisterVendorSerializer,
    UserProfileSerializer,
    VerifyEmailConfirmSerializer,
)
from .services import issue_password_reset_token, issue_verification_token


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
        serializer = RegisterVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user, shop = serializer.save()

        try:
            issue_verification_token(user)
        except Exception:
            pass

        access, refresh = self.issue_tokens(user)
        response = Response(
            {
                "access": access,
                "user": UserProfileSerializer(user).data,
                "shops": ShopBriefSerializer([shop], many=True).data,
            },
            status=status.HTTP_201_CREATED,
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
        if request.user.role == request.user.Role.VENDOR:
            data["shops"] = ShopBriefSerializer(request.user.shops.all(), many=True).data
        return Response(data)


class VerifyEmailRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        if not request.user.is_email_verified:
            issue_verification_token(request.user)
        return Response(status=status.HTTP_202_ACCEPTED)


class VerifyEmailConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]

        try:
            token = EmailVerificationToken.objects.select_related("user").get(token=raw_token)
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if token.user.is_email_verified:
            return Response({"detail": "Email already verified."}, status=status.HTTP_200_OK)

        if not token.is_valid():
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
            token.user.is_email_verified = True
            token.user.save(update_fields=["is_email_verified"])

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
            {"detail": "If that email is registered, a reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            token = PasswordResetToken.objects.select_related("user").get(token=raw_token)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not token.is_valid():
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])

            user = token.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            for outstanding in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=outstanding)

        return Response(
            {"detail": "Password updated. Please log in again."}, status=status.HTTP_200_OK
        )
