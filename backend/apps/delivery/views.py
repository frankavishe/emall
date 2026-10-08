from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.services import blacklist_all_tokens
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator, IsRider
from apps.delivery.serializers import (
    ACTIVE_DELIVERY_STATUSES,
    AdminRiderCreateSerializer,
    AdminRiderSerializer,
    AdminRiderUpdateSerializer,
    RiderDeliverySerializer,
    RiderDeliveryStatusSerializer,
)
from apps.orders.models import OrderItem
from apps.orders.services import TransitionError, advance_order_item_status


def _riders():
    return (
        User.objects.filter(role=User.Role.RIDER)
        .select_related("rider_profile")
        .annotate(
            active_delivery_count=Count(
                "deliveries", filter=Q(deliveries__status__in=ACTIVE_DELIVERY_STATUSES)
            )
        )
    )


class AdminRiderListCreateView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminRiderSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = _riders().order_by("name")
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset

    def post(self, request):
        serializer = AdminRiderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rider = serializer.save()
        return Response(
            AdminRiderSerializer(_riders().get(pk=rider.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class AdminRiderDetailView(APIView):
    permission_classes = [IsAdministrator]

    def patch(self, request, rider_id):
        rider = get_object_or_404(
            User.objects.select_related("rider_profile"), pk=rider_id, role=User.Role.RIDER
        )
        serializer = AdminRiderUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        was_active = rider.is_active
        with transaction.atomic():
            serializer.update(rider, serializer.validated_data)
            # Deactivation or a new password logs the rider out of every device.
            if (was_active and not rider.is_active) or "password" in serializer.validated_data:
                blacklist_all_tokens(rider)

        return Response(AdminRiderSerializer(_riders().get(pk=rider.pk)).data)


class RiderDeliveryListView(ListAPIView):
    """The requesting rider's own deliveries. `?scope=completed` lists delivered/cancelled
    lines; anything else lists the active ones (processing or shipped)."""

    permission_classes = [IsRider]
    serializer_class = RiderDeliverySerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = OrderItem.objects.filter(rider=self.request.user).select_related(
            "product", "product__shop", "order"
        )
        if self.request.query_params.get("scope") == "completed":
            return queryset.exclude(status__in=ACTIVE_DELIVERY_STATUSES).order_by(
                "-rider_assigned_at"
            )
        return queryset.filter(status__in=ACTIVE_DELIVERY_STATUSES).order_by("rider_assigned_at")


class RiderDeliveryStatusView(APIView):
    """Scoped to the requesting rider's own lines, so anyone else's line ID 404s."""

    permission_classes = [IsRider]

    def patch(self, request, item_id):
        order_item = get_object_or_404(
            OrderItem.objects.select_related("product", "product__shop", "order"),
            pk=item_id,
            rider=request.user,
        )
        serializer = RiderDeliveryStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            advance_order_item_status(
                order_item=order_item, new_status=serializer.validated_data["status"]
            )
        except TransitionError as error:
            return Response({"status": [str(error)]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RiderDeliverySerializer(order_item).data)
