import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.email import get_email_service
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator, IsCustomer
from apps.realtime.broadcast import publish_on_commit
from apps.realtime.groups import ADMINS, user_group
from apps.vendors.models import Shop
from apps.vendors.serializers import (
    AdminShopListSerializer,
    ShopDescriptionSerializer,
    ShopLocationSerializer,
    ShopLogoSerializer,
    ShopSerializer,
    ShopThemeSerializer,
)

logger = logging.getLogger(__name__)


class VendorShopListCreateView(ListCreateAPIView):
    # IsCustomer = any non-admin account: a customer opening their first shop becomes a vendor
    # on the same account (one email, both roles).
    permission_classes = [IsCustomer]
    serializer_class = ShopSerializer
    pagination_class = None

    def get_queryset(self):
        return Shop.objects.filter(owner=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            shop = serializer.save()
            if not request.user.is_vendor:
                request.user.is_vendor = True
                request.user.save(update_fields=["is_vendor"])
        return Response(self.get_serializer(shop).data, status=status.HTTP_201_CREATED)


class VendorShopLogoView(APIView):
    """Upload/replace (PUT) or remove (DELETE) a shop's logo. Ownership only — a logo can be
    set whatever the shop's approval status, and changing it doesn't trigger re-approval."""

    permission_classes = [IsCustomer]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        serializer = ShopLogoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if shop.logo:
            shop.logo.delete(save=False)
        shop.logo = serializer.validated_data["logo"]
        shop.save(update_fields=["logo"])
        return Response(ShopSerializer(shop, context={"request": request}).data)

    def delete(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        if shop.logo:
            shop.logo.delete(save=False)
            shop.logo = None
            shop.save(update_fields=["logo"])
        return Response(ShopSerializer(shop, context={"request": request}).data)


class VendorShopThemeView(APIView):
    """Set or reset (PATCH) a shop's primary/accent colors. Like the logo: ownership only, any
    approval status, no re-approval."""

    permission_classes = [IsCustomer]

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        serializer = ShopThemeSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ShopSerializer(shop, context={"request": request}).data)


class VendorShopDescriptionView(APIView):
    """Set or clear (PATCH) a shop's storefront description. Ownership only, any approval status,
    no re-approval."""

    permission_classes = [IsCustomer]

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        serializer = ShopDescriptionSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ShopSerializer(shop, context={"request": request}).data)


def _save_shop_location(request, shop):
    serializer = ShopLocationSerializer(shop, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(ShopSerializer(shop, context={"request": request}).data)


class VendorShopLocationView(APIView):
    """Set (PUT) a shop's pickup location (007-delivery-fee). Ownership only, any approval
    status, no re-approval."""

    permission_classes = [IsCustomer]

    def put(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        return _save_shop_location(request, shop)


class AdminShopLocationView(APIView):
    """An Administrator sets or corrects any shop's pickup location."""

    permission_classes = [IsAdministrator]

    def put(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        return _save_shop_location(request, shop)


class AdminShopListView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminShopListSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = Shop.objects.select_related("owner").order_by("-created_at")
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


def _announce_shop_change(shop):
    """Tells the owner's open tabs (and other admins) to refetch, so a shop goes live for its
    vendor the moment it is approved."""

    publish_on_commit(
        [user_group(shop.owner_id), ADMINS], {"type": "shop.updated", "shop_id": shop.id}
    )


def _send_shop_approved_email(shop):
    """Best-effort, like `send_order_confirmation`: the approval is already committed."""

    try:
        get_email_service().send_shop_approved_email(shop)
    except Exception:
        logger.exception("Failed to send shop approval email for shop_id=%s", shop.id)


class AdminShopApproveView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, shop_id):
        with transaction.atomic():
            shop = get_object_or_404(
                Shop.objects.select_related("owner").select_for_update(), pk=shop_id
            )
            if shop.status != Shop.Status.PENDING:
                return Response(
                    {"detail": "Only a pending shop can be approved."},
                    status=status.HTTP_409_CONFLICT,
                )
            # No email-verification gate here: the owner already verified at sign-up, so an
            # Administrator's approval takes effect immediately.
            shop.status = Shop.Status.APPROVED
            shop.status_changed_at = timezone.now()
            shop.save(update_fields=["status", "status_changed_at"])
            _announce_shop_change(shop)
            transaction.on_commit(lambda: _send_shop_approved_email(shop))
        return Response(ShopSerializer(shop).data, status=status.HTTP_200_OK)


class AdminShopRejectView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, shop_id):
        with transaction.atomic():
            shop = get_object_or_404(Shop.objects.select_for_update(), pk=shop_id)
            if shop.status != Shop.Status.PENDING:
                return Response(
                    {"detail": "Only a pending shop can be rejected."},
                    status=status.HTTP_409_CONFLICT,
                )
            shop.status = Shop.Status.REJECTED
            shop.status_reason = request.data.get("reason")
            shop.status_changed_at = timezone.now()
            shop.save(update_fields=["status", "status_reason", "status_changed_at"])
            _announce_shop_change(shop)
        return Response(ShopSerializer(shop).data, status=status.HTTP_200_OK)
