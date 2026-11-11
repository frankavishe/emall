from django.conf import settings
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import changed_fields, record
from apps.bookings.models import Booking, OpeningHours, Service, ShopClosure
from apps.bookings.permissions import (
    owned_bookable_shop,
    owned_services_shop,
    require_bookable_shop,
)
from apps.bookings.serializers import (
    AdminBookingCancelSerializer,
    AdminBookingDetailSerializer,
    AdminBookingSerializer,
    BookingDetailSerializer,
    BookingPaySerializer,
    BookingReasonSerializer,
    BookingRequestSerializer,
    BookingSerializer,
    ClosureBookingSerializer,
    OpeningPeriodSerializer,
    PublicServiceSerializer,
    ShopClosureSerializer,
    ShopScheduleSerializer,
    VendorBookingDetailSerializer,
    VendorBookingSerializer,
    VendorServiceSerializer,
    VendorServiceWriteSerializer,
    latest_payment,
)
from apps.bookings.services import (
    accept_booking,
    admin_cancel_booking,
    booking_payment_methods,
    cancel_customer_booking,
    decline_booking,
    provider_cancel_booking,
    refresh_bookings,
    request_booking,
    start_booking_payment,
)
from apps.bookings.slots import market_day_bounds, market_today, open_slots
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import (
    AdminArea,
    IsCustomer,
    IsCustomerOrGuest,
    IsVendor,
    require_verified_email,
)
from apps.core.throttles import GuestScopedRateThrottle
from apps.payments.outcomes import SettlementError, settle_manual_payment
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


def _parse_local_date(value, field="date"):
    try:
        parsed = parse_date(value or "")
    except ValueError:
        parsed = None
    if parsed is None:
        raise ValidationError({field: "Enter a date as YYYY-MM-DD."})
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
        # Existing bookings stand: the provider is warned and deals with each one themselves.
        active = (
            Booking.objects.holding()
            .filter(shop=shop)
            .overlapping(*market_day_bounds(closure.date))
            .select_related("service", "customer")
            .order_by("starts_at")
        )
        warnings = ClosureBookingSerializer(active, many=True).data
        return Response(
            {**serializer.data, "active_bookings": warnings}, status=status.HTTP_201_CREATED
        )


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


# --- Bookings ------------------------------------------------------------------


def _with_status(queryset, params):
    wanted = params.get("status")
    return queryset.filter(status=wanted) if wanted else queryset


def _with_shop(queryset, params):
    shop = params.get("shop")
    if not shop:
        return queryset
    return queryset.filter(shop_id=shop) if shop.isdigit() else queryset.none()


def _booking_rows():
    return Booking.objects.select_related("service", "shop")


def booking_detail_rows():
    return _booking_rows().prefetch_related("status_events", "payments__refunds")


# --- Customer: bookings --------------------------------------------------------


class BookingListCreateView(ListCreateAPIView):
    """Listing is for signed-in customers. Requesting is open to guests too (no account), who
    get the booking's `access_token` back as their only way to reach it again."""

    pagination_class = LimitedPageNumberPagination
    serializer_class = BookingSerializer
    throttle_scope = "booking_request"

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsCustomerOrGuest()]
        return [IsCustomer()]

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        return _with_status(
            _booking_rows().filter(customer=self.request.user), self.request.query_params
        )

    def list(self, request, *args, **kwargs):
        refresh_bookings(Booking.objects.filter(customer=request.user))
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        is_guest = not request.user.is_authenticated
        if not is_guest:
            require_verified_email(request.user)
        serializer = BookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if is_guest:
            missing = {
                field: ["This field is required."]
                for field in ("name", "email")
                if not data[field].strip()
            }
            if missing:
                raise ValidationError(missing)
        booking = request_booking(
            customer=None if is_guest else request.user,
            guest_name=data["name"].strip() if is_guest else "",
            guest_email=data["email"].strip() if is_guest else "",
            service_id=data["service"],
            starts_at=data["starts_at"],
            contact_phone=data["contact_phone"],
            customer_note=data["customer_note"],
            request=request,
        )
        body = BookingSerializer(booking).data
        if booking.is_guest:
            body["access_token"] = booking.access_token
        return Response(body, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request, booking_id):
        refresh_bookings(Booking.objects.filter(pk=booking_id, customer=request.user))
        booking = get_object_or_404(booking_detail_rows(), pk=booking_id, customer=request.user)
        return Response(BookingDetailSerializer(booking).data)


class BookingCancelView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, booking_id):
        booking = cancel_customer_booking(
            booking_id=booking_id, customer=request.user, request=request
        )
        return Response(BookingSerializer(booking).data)


class _GuestBookingView(APIView):
    """A guest booking is reached only through its unguessable `access_token`, so an unknown
    token simply 404s. No authentication: the token is the credential."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [GuestScopedRateThrottle]
    throttle_scope = "guest_order"


class GuestBookingDetailView(_GuestBookingView):
    """`GET /api/bookings/track/{token}`."""

    def get(self, request, token):
        refresh_bookings(Booking.objects.filter(customer__isnull=True, access_token=token))
        booking = get_object_or_404(
            booking_detail_rows(), customer__isnull=True, access_token=token
        )
        return Response(BookingDetailSerializer(booking).data)


class GuestBookingCancelView(_GuestBookingView):
    """`POST /api/bookings/track/{token}/cancel`."""

    def post(self, request, token):
        booking = get_object_or_404(
            Booking.objects.only("id"), customer__isnull=True, access_token=token
        )
        booking = cancel_customer_booking(
            booking_id=booking.id, access_token=token, request=request
        )
        return Response(BookingSerializer(booking).data)


# --- Customer and guest: payment -----------------------------------------------


def payment_status_data(booking):
    payment = latest_payment(booking)
    return {
        "booking_id": booking.id,
        "booking_status": booking.status,
        "pay_by": BookingSerializer(booking).data["pay_by"],
        "payment_status": payment.status if payment else None,
        "method": payment.method if payment else None,
        "failure_reason": payment.failure_reason if payment else "",
    }


def _customer_scope(customer=None, access_token=None):
    """`owner` below is one of `{"customer": user}` or `{"access_token": token}`: the same
    endpoints serve a signed-in customer by id and a guest through their tracking link."""

    if customer is not None:
        return Booking.objects.filter(customer=customer)
    return Booking.objects.filter(customer__isnull=True, access_token=access_token)


def _payment_methods_response(booking_id, owner):
    booking = get_object_or_404(_customer_scope(**owner), pk=booking_id)
    if booking.status != Booking.Status.AWAITING_PAYMENT:
        return Response([])
    return Response(booking_payment_methods(booking))


def _pay_response(request, booking_id, owner):
    serializer = BookingPaySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    start_booking_payment(booking_id=booking_id, **owner, **serializer.validated_data)
    booking = booking_detail_rows().get(pk=booking_id)
    return Response(BookingDetailSerializer(booking).data, status=status.HTTP_201_CREATED)


def _payment_status_response(booking_id, owner):
    scope = _customer_scope(**owner).filter(pk=booking_id)
    refresh_bookings(scope)
    booking = get_object_or_404(scope.prefetch_related("payments"))
    return Response(payment_status_data(booking))


class BookingPaymentMethodsView(APIView):
    """`GET /api/bookings/{id}/payment-methods`."""

    permission_classes = [IsCustomer]

    def get(self, request, booking_id):
        return _payment_methods_response(booking_id, {"customer": request.user})


class BookingPayView(APIView):
    """`POST /api/bookings/{id}/pay`."""

    permission_classes = [IsCustomer]

    def post(self, request, booking_id):
        return _pay_response(request, booking_id, {"customer": request.user})


class BookingPaymentStatusView(APIView):
    """`GET /api/bookings/{id}/payment-status`: polled while a push is pending."""

    permission_classes = [IsCustomer]

    def get(self, request, booking_id):
        return _payment_status_response(booking_id, {"customer": request.user})


def _guest_booking_id(token):
    return get_object_or_404(
        Booking.objects.only("id"), customer__isnull=True, access_token=token
    ).id


class GuestBookingPaymentMethodsView(_GuestBookingView):
    """`GET /api/bookings/track/{token}/payment-methods`."""

    def get(self, request, token):
        return _payment_methods_response(_guest_booking_id(token), {"access_token": token})


class GuestBookingPayView(_GuestBookingView):
    """`POST /api/bookings/track/{token}/pay`."""

    def post(self, request, token):
        return _pay_response(request, _guest_booking_id(token), {"access_token": token})


class GuestBookingPaymentStatusView(_GuestBookingView):
    """`GET /api/bookings/track/{token}/payment-status`."""

    def get(self, request, token):
        return _payment_status_response(_guest_booking_id(token), {"access_token": token})


# --- Provider: bookings --------------------------------------------------------


class VendorBookingListView(ListAPIView):
    permission_classes = [IsVendor]
    pagination_class = LimitedPageNumberPagination
    serializer_class = VendorBookingSerializer

    def get_queryset(self):
        queryset = _booking_rows().select_related("customer").filter(shop__owner=self.request.user)
        params = self.request.query_params
        return _with_shop(_with_status(queryset, params), params)

    def list(self, request, *args, **kwargs):
        refresh_bookings(Booking.objects.filter(shop__owner=request.user))
        return super().list(request, *args, **kwargs)


class VendorBookingDetailView(APIView):
    permission_classes = [IsVendor]

    def get(self, request, booking_id):
        refresh_bookings(Booking.objects.filter(pk=booking_id, shop__owner=request.user))
        booking = get_object_or_404(
            _booking_rows().select_related("customer").prefetch_related("status_events"),
            pk=booking_id,
            shop__owner=request.user,
        )
        return Response(VendorBookingDetailSerializer(booking).data)


class VendorBookingAcceptView(APIView):
    permission_classes = [IsVendor]

    def post(self, request, booking_id):
        booking = accept_booking(booking_id=booking_id, owner=request.user, request=request)
        return Response(VendorBookingSerializer(booking).data)


class VendorBookingDeclineView(APIView):
    permission_classes = [IsVendor]

    def post(self, request, booking_id):
        serializer = BookingReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = decline_booking(
            booking_id=booking_id,
            owner=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(VendorBookingSerializer(booking).data)


class VendorBookingCancelView(APIView):
    """`POST /api/vendor/bookings/{id}/cancel`: a reason is required, and the customer sees it."""

    permission_classes = [IsVendor]

    def post(self, request, booking_id):
        serializer = BookingReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = provider_cancel_booking(
            booking_id=booking_id,
            owner=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(VendorBookingSerializer(booking).data)


# --- Administrator: bookings ---------------------------------------------------


class AdminBookingListView(ListAPIView):
    permission_classes = [AdminArea("bookings")]
    pagination_class = LimitedPageNumberPagination
    serializer_class = AdminBookingSerializer

    def get_queryset(self):
        params = self.request.query_params
        queryset = _booking_rows().select_related("customer")
        queryset = _with_shop(_with_status(queryset, params), params)
        search = (params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(customer__email__icontains=search)
                | models.Q(customer__name__icontains=search)
                | models.Q(guest_email__icontains=search)
                | models.Q(guest_name__icontains=search)
                | models.Q(shop__name__icontains=search)
                | models.Q(service__name__icontains=search)
            )
        if params.get("date_from"):
            start, _ = market_day_bounds(_parse_local_date(params["date_from"], "date_from"))
            queryset = queryset.filter(starts_at__gte=start)
        if params.get("date_to"):
            _, end = market_day_bounds(_parse_local_date(params["date_to"], "date_to"))
            queryset = queryset.filter(starts_at__lt=end)
        return queryset

    def list(self, request, *args, **kwargs):
        refresh_bookings()
        return super().list(request, *args, **kwargs)


class AdminBookingDetailView(APIView):
    permission_classes = [AdminArea("bookings")]

    def get(self, request, booking_id):
        refresh_bookings(Booking.objects.filter(pk=booking_id))
        return Response(_admin_booking_data(booking_id))


def _admin_booking_data(booking_id):
    booking = get_object_or_404(
        _booking_rows()
        .select_related("customer")
        .prefetch_related("status_events__actor", "payments__refunds"),
        pk=booking_id,
    )
    return AdminBookingDetailSerializer(booking).data


class AdminBookingCancelView(APIView):
    """`POST /api/admin/bookings/{id}/cancel`: body `reason`, optional `refund_amount`."""

    permission_classes = [AdminArea("bookings")]

    def post(self, request, booking_id):
        serializer = AdminBookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin_cancel_booking(
            booking_id=booking_id,
            admin=request.user,
            reason=serializer.validated_data["reason"],
            refund_amount=serializer.validated_data.get("refund_amount"),
            request=request,
        )
        return Response(_admin_booking_data(booking_id))


class AdminBookingPaymentSettleView(APIView):
    """`POST /api/admin/bookings/{id}/payment/confirm` (or `/reject`, with an optional
    `reason`): an administrator checking a Lipa Namba payment against the statement."""

    permission_classes = [AdminArea("bookings", write_permission="finance.manage")]
    confirm = True

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id)
        serializer = BookingReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"].strip()
        try:
            settle_manual_payment(
                booking=booking, admin=request.user, confirm=self.confirm, reason=reason
            )
        except SettlementError as error:
            return Response({"detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)
        record(
            AuditAction.PAYMENT_CONFIRMED if self.confirm else AuditAction.PAYMENT_REJECTED,
            request=request,
            target=booking,
            target_repr=f"Booking #{booking.pk}",
            metadata={"reason": reason} if reason else {},
        )
        return Response(_admin_booking_data(booking_id))
