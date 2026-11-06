from django.conf import settings
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import changed_fields, record
from apps.bookings.models import OpeningHours, Service, ShopClosure
from apps.bookings.permissions import (
    owned_bookable_shop,
    owned_services_shop,
    require_bookable_shop,
)
from apps.bookings.serializers import (
    OpeningPeriodSerializer,
    PublicServiceSerializer,
    ShopClosureSerializer,
    ShopScheduleSerializer,
    VendorServiceSerializer,
    VendorServiceWriteSerializer,
)
from apps.bookings.slots import market_today, open_slots
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsVendor
from apps.vendors.models import Shop

# --- Public --------------------------------------------------------------------


class CatalogServiceListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicServiceSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = (
            Service.objects.visible().select_related("shop", "category").order_by("-created_at")
        )
        params = self.request.query_params
        search = (params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | models.Q(description__icontains=search)
            )
        shop = params.get("shop")
        if shop:
            if not shop.isdigit():
                return queryset.none()
            queryset = queryset.filter(shop_id=shop)
        category = params.get("category")
        if category:
            # A top-level category also matches services in its subcategories.
            queryset = queryset.filter(
                models.Q(category__slug=category) | models.Q(category__parent__slug=category)
            )
        return queryset


class CatalogServiceDetailView(APIView):
    """Uniform 404 for anything the public can't see, as for products."""

    permission_classes = [AllowAny]

    def get(self, request, service_id):
        service = get_object_or_404(
            Service.objects.visible().select_related("shop", "category"), pk=service_id
        )
        return Response(PublicServiceSerializer(service, context={"request": request}).data)


def _parse_local_date(value):
    try:
        parsed = parse_date(value or "")
    except ValueError:
        parsed = None
    if parsed is None:
        raise ValidationError({"date": "Enter a date as YYYY-MM-DD."})
    return parsed


class CatalogServiceSlotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, service_id):
        service = get_object_or_404(Service.objects.visible().select_related("shop"), pk=service_id)
        local_date = _parse_local_date(request.query_params.get("date"))
        return Response(
            {
                "date": local_date.isoformat(),
                "time_zone": settings.MARKET_TIME_ZONE,
                "slots": [
                    {
                        "starts_at": slot.starts_at.isoformat(),
                        "ends_at": slot.ends_at.isoformat(),
                    }
                    for slot in open_slots(service, local_date)
                ],
            }
        )


# --- Provider: services --------------------------------------------------------


def _owned_service(request, service_id):
    return get_object_or_404(
        Service.objects.select_related("shop", "category"),
        pk=service_id,
        shop__owner=request.user,
        is_archived=False,
    )


class VendorServiceListCreateView(ListCreateAPIView):
    permission_classes = [IsVendor]
    pagination_class = LimitedPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VendorServiceWriteSerializer
        return VendorServiceSerializer

    def get_queryset(self):
        return (
            Service.objects.filter(shop__owner=self.request.user, is_archived=False)
            .select_related("shop", "category")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        record(
            AuditAction.SERVICE_CREATED,
            request=request,
            target=service,
            metadata={"shop_id": service.shop_id},
        )
        return Response(VendorServiceSerializer(service).data, status=status.HTTP_201_CREATED)


class VendorServiceDetailView(APIView):
    permission_classes = [IsVendor]

    def get(self, request, service_id):
        return Response(VendorServiceSerializer(_owned_service(request, service_id)).data)

    def patch(self, request, service_id):
        service = _owned_service(request, service_id)
        require_bookable_shop(service.shop)
        serializer = VendorServiceWriteSerializer(
            service, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        fields = changed_fields(service, serializer.validated_data)
        serializer.save()
        if fields:
            record(
                AuditAction.SERVICE_UPDATED,
                request=request,
                target=service,
                metadata={"fields": fields},
            )
        return Response(VendorServiceSerializer(service).data)

    def delete(self, request, service_id):
        service = _owned_service(request, service_id)
        require_bookable_shop(service.shop)
        service.is_archived = True
        service.is_published = False
        service.save(update_fields=["is_archived", "is_published", "updated_at"])
        record(AuditAction.SERVICE_ARCHIVED, request=request, target=service)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorServicePublishView(APIView):
    permission_classes = [IsVendor]

    def post(self, request, service_id):
        service = _owned_service(request, service_id)
        require_bookable_shop(service.shop)
        if not service.shop.has_location:
            return Response(
                {"detail": "Set your shop's location before publishing a service."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service.is_published = True
        service.save(update_fields=["is_published", "updated_at"])
        record(AuditAction.SERVICE_PUBLISHED, request=request, target=service)
        return Response(VendorServiceSerializer(service).data)


class VendorServiceUnpublishView(APIView):
    permission_classes = [IsVendor]

    def post(self, request, service_id):
        service = _owned_service(request, service_id)
        require_bookable_shop(service.shop)
        service.is_published = False
        service.save(update_fields=["is_published", "updated_at"])
        record(AuditAction.SERVICE_UNPUBLISHED, request=request, target=service)
        return Response(VendorServiceSerializer(service).data)


# --- Provider: schedule --------------------------------------------------------


def _schedule_response(shop):
    return Response(
        {
            "booking_capacity": shop.booking_capacity,
            "hours": OpeningPeriodSerializer(shop.opening_hours.all(), many=True).data,
        }
    )


class VendorShopScheduleView(APIView):
    permission_classes = [IsVendor]

    def get(self, request, shop_id):
        return _schedule_response(owned_services_shop(request, shop_id))

    def put(self, request, shop_id):
        shop = owned_bookable_shop(request, shop_id)
        serializer = ShopScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            # Serialises two saves of the same schedule, so they can't mix their periods.
            shop = Shop.objects.select_for_update(no_key=True).get(pk=shop.pk)
            shop.booking_capacity = serializer.validated_data["booking_capacity"]
            shop.save(update_fields=["booking_capacity"])
            shop.opening_hours.all().delete()
            OpeningHours.objects.bulk_create(
                OpeningHours(shop=shop, **period) for period in serializer.validated_data["hours"]
            )
            record(AuditAction.SHOP_SCHEDULE_UPDATED, request=request, target=shop)
        return _schedule_response(shop)


class VendorShopClosureListCreateView(ListCreateAPIView):
    permission_classes = [IsVendor]
    pagination_class = LimitedPageNumberPagination
    serializer_class = ShopClosureSerializer

    def get_queryset(self):
        shop = owned_services_shop(self.request, self.kwargs["shop_id"])
        return ShopClosure.objects.filter(shop=shop, date__gte=market_today()).order_by("date")

    def create(self, request, *args, **kwargs):
        shop = owned_bookable_shop(request, kwargs["shop_id"])
        serializer = ShopClosureSerializer(data=request.data, context={"shop": shop})
        serializer.is_valid(raise_exception=True)
        closure = serializer.save(shop=shop)
        record(
            AuditAction.SHOP_SCHEDULE_UPDATED,
            request=request,
            target=shop,
            metadata={"closure_added": closure.date},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VendorShopClosureDetailView(APIView):
    permission_classes = [IsVendor]

    def delete(self, request, shop_id, closure_id):
        shop = owned_bookable_shop(request, shop_id)
        closure = get_object_or_404(ShopClosure, pk=closure_id, shop=shop)
        record(
            AuditAction.SHOP_SCHEDULE_UPDATED,
            request=request,
            target=shop,
            metadata={"closure_removed": closure.date},
        )
        closure.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
