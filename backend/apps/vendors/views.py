from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdministrator, IsVendor
from apps.vendors.models import Shop
from apps.vendors.serializers import AdminShopListSerializer, ShopSerializer


class VendorShopListCreateView(ListCreateAPIView):
    permission_classes = [IsVendor]
    serializer_class = ShopSerializer
    pagination_class = None

    def get_queryset(self):
        return Shop.objects.filter(owner=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()
        return Response(self.get_serializer(shop).data, status=status.HTTP_201_CREATED)


class AdminShopListView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminShopListSerializer

    def get_queryset(self):
        queryset = Shop.objects.select_related("owner").order_by("-created_at")
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


class AdminShopApproveView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, shop_id):
        with transaction.atomic():
            shop = get_object_or_404(Shop.objects.select_for_update(), pk=shop_id)
            if shop.status != Shop.Status.PENDING:
                return Response(
                    {"detail": "Only a pending shop can be approved."},
                    status=status.HTTP_409_CONFLICT,
                )
            shop.status = Shop.Status.APPROVED
            shop.status_changed_at = timezone.now()
            shop.save(update_fields=["status", "status_changed_at"])
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
        return Response(ShopSerializer(shop).data, status=status.HTTP_200_OK)
