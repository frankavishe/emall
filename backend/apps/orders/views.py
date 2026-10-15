from decimal import Decimal

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.cart.services import resolve_cart
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator, IsCustomer, IsCustomerOrGuest, IsVendor
from apps.core.throttles import GuestScopedRateThrottle
from apps.orders.models import Order, OrderItem, OrderItemStatusEvent
from apps.orders.serializers import (
    AdminOrderItemSerializer,
    AssignRiderSerializer,
    CheckoutSerializer,
    DeliveryPinSerializer,
    OrderDetailSerializer,
    OrderItemStatusUpdateSerializer,
    OrderSerializer,
    VendorOrderItemSerializer,
)
from apps.orders.services import (
    AssignmentError,
    CheckoutError,
    TransitionError,
    advance_order_item_status,
    assign_rider,
    place_order,
    quote_cart_delivery,
)
from apps.payments.models import PaymentRecord
from apps.payments.outcomes import expire_stale_payments
from apps.vendors.models import Shop


class CheckoutView(APIView):
    """Re-validates the cart, charges the mock payment service, and — only if both succeed —
    creates the Order atomically (research.md §4). Every failure case is translated to the `400`
    response shapes in contracts/cart-checkout-api.md. Mobile money instead answers `202` with an
    AWAITING_PAYMENT order (see `place_order()`), or `409 payment_pending` while one exists; so
    does Lipa Namba, whose order waits for an administrator to find the payment.

    Guests (guest checkout) must give an `email`; their response carries the order's
    `access_token`, the only way back to a guest order."""

    permission_classes = [IsCustomerOrGuest]
    throttle_classes = [GuestScopedRateThrottle]
    throttle_scope = "guest_checkout"

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_guest = not request.user.is_authenticated
        if is_guest and not data.get("email"):
            raise ValidationError({"email": ["Enter your email address."]})

        try:
            order = place_order(
                cart=resolve_cart(request, create=False),
                guest_email=data.get("email", "") if is_guest else "",
                shipping_data=data["shipping"],
                payment_method=data["payment_method"],
                msisdn=data.get("msisdn"),
                provider=data.get("provider"),
                payer_reference=data.get("payer_reference", ""),
            )
        except CheckoutError as error:
            body = {"detail": error.detail, **error.extra}
            if error.code in CODED_CHECKOUT_ERRORS:
                body["code"] = error.code
            http_status = (
                status.HTTP_409_CONFLICT
                if error.code == "payment_pending"
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(body, status=http_status)

        # 202: a mobile-money order exists but waits for the customer to approve the push.
        http_status = (
            status.HTTP_202_ACCEPTED
            if order.status == Order.Status.AWAITING_PAYMENT
            else status.HTTP_201_CREATED
        )
        return Response(order_detail_data(order), status=http_status)


def order_detail_data(order):
    """`OrderDetailSerializer` output, plus the private `access_token` for a guest order."""

    data = OrderDetailSerializer(order).data
    if order.is_guest:
        data["access_token"] = order.access_token
    return data


# Checkout failures whose `code` is returned so the client can react to them specifically.
CODED_CHECKOUT_ERRORS = {
    "payment_failed",
    "payment_pending",
    "shop_without_location",
    "out_of_range",
}


def _money(value):
    return str(value.quantize(Decimal("0.01")))


class DeliveryQuoteView(APIView):
    """`POST /api/checkout/delivery-quote`: prices delivery of the requester's cart to a pin
    (007-delivery-fee). Advisory only; checkout recomputes it."""

    permission_classes = [IsCustomerOrGuest]
    throttle_classes = [GuestScopedRateThrottle]
    throttle_scope = "guest_checkout"

    def post(self, request):
        serializer = DeliveryPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            quote = quote_cart_delivery(
                cart=resolve_cart(request, create=False), **serializer.validated_data
            )
        except CheckoutError as error:
            return Response(
                {"detail": error.detail, "code": error.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "legs": [
                    {
                        "shop_id": leg.shop.id,
                        "shop_name": leg.shop.name,
                        "distance_km": _money(leg.distance_km),
                        "fee": _money(leg.fee),
                    }
                    for leg in quote["legs"]
                ],
                "items_subtotal": _money(quote["items_subtotal"]),
                "delivery_fee": _money(quote["delivery_fee"]),
                "total": _money(quote["total"]),
            }
        )


class OrderListView(ListAPIView):
    """Lists only the requester's own orders, most recent first (FR-020)."""

    permission_classes = [IsCustomer]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by("-placed_at")


class OrderDetailView(APIView):
    """Scoped to the requester's own orders at the queryset level, so another Customer's order
    ID 404s rather than 403ing (FR-021, research.md §6)."""

    permission_classes = [IsCustomer]

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, customer=request.user)
        return Response(OrderDetailSerializer(order).data)


class OrderPaymentStatusView(APIView):
    """`GET /api/orders/{id}/payment-status`: what the "check your phone" page polls while a
    mobile-money payment is pending. Expires the payment on the spot if it has timed out."""

    permission_classes = [IsCustomer]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("payment"), pk=order_id, customer=request.user
        )
        return Response(payment_status_data(order))


def payment_status_data(order):
    """Expires the order's payment on the spot if it has timed out, then reports its state."""

    payment = getattr(order, "payment", None)
    if payment is not None and payment.status == PaymentRecord.Status.PENDING:
        expire_stale_payments(queryset=PaymentRecord.objects.filter(pk=payment.pk))
        order.refresh_from_db()
        payment.refresh_from_db()
    return {
        "order_id": order.id,
        "order_status": order.status,
        "payment_status": payment.status if payment else None,
        "failure_reason": payment.failure_reason if payment else "",
    }


class _GuestOrderView(APIView):
    """A guest order (guest checkout) is reached only through its unguessable `access_token`,
    so an unknown token simply 404s. No authentication: the token is the credential."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [GuestScopedRateThrottle]
    throttle_scope = "guest_order"

    def get_order(self, token):
        return get_object_or_404(Order.objects.select_related("payment"), access_token=token)


class GuestOrderDetailView(_GuestOrderView):
    """`GET /api/orders/track/{token}`."""

    def get(self, request, token):
        return Response(order_detail_data(self.get_order(token)))


class GuestOrderPaymentStatusView(_GuestOrderView):
    """`GET /api/orders/track/{token}/payment-status`: the guest's "check your phone" poll."""

    def get(self, request, token):
        return Response(payment_status_data(self.get_order(token)))


class VendorOrderItemListView(ListAPIView):
    """Lists only order lines whose product belongs to one of the requester's own shops, across
    every Customer's order (FR-001, FR-004)."""

    permission_classes = [IsVendor]
    serializer_class = VendorOrderItemSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        return (
            OrderItem.objects.filter(
                product__shop__owner=self.request.user, order__status=Order.Status.PLACED
            )
            .select_related("product", "product__shop", "order", "rider__rider_profile")
            .order_by("-order__placed_at")
        )


class VendorOrderItemStatusUpdateView(APIView):
    """Scoped to the requester's own shops at the queryset level, so another vendor's line ID
    404s rather than 403ing (FR-004); additionally requires the owning shop to be APPROVED
    (FR-010) before any transition is attempted."""

    permission_classes = [IsVendor]

    def patch(self, request, item_id):
        order_item = get_object_or_404(
            OrderItem.objects.select_related("product", "product__shop", "order"),
            pk=item_id,
            product__shop__owner=request.user,
            order__status=Order.Status.PLACED,
        )
        if order_item.product.shop.status != Shop.Status.APPROVED:
            raise PermissionDenied(
                "Your shop must be approved to update fulfillment status."
            )

        serializer = OrderItemStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            advance_order_item_status(
                order_item=order_item, new_status=serializer.validated_data["status"]
            )
        except TransitionError as error:
            return Response({"status": [str(error)]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(VendorOrderItemSerializer(order_item).data)


class AdminOrderItemListView(ListAPIView):
    """Read-only oversight across every shop/vendor's order lines, each with its full
    status-change history (FR-007, FR-008, FR-009)."""

    permission_classes = [IsAdministrator]
    serializer_class = AdminOrderItemSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = (
            OrderItem.objects.select_related(
                "product", "product__shop", "order", "rider__rider_profile"
            )
            .prefetch_related(
                Prefetch(
                    "status_events",
                    queryset=OrderItemStatusEvent.objects.order_by("changed_at"),
                )
            )
            .filter(order__status=Order.Status.PLACED)
            .order_by("-order__placed_at")
        )
        shop = self.request.query_params.get("shop", "")
        if shop.isdigit():
            queryset = queryset.filter(product__shop_id=int(shop))
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        order = self.request.query_params.get("order", "")
        if order.isdigit():
            queryset = queryset.filter(order_id=int(order))
        return queryset


class AdminOrderItemAssignRiderView(APIView):
    """Assigns a delivery rider to an order line (`{"rider_id": null}` unassigns)."""

    permission_classes = [IsAdministrator]

    def post(self, request, item_id):
        serializer = AssignRiderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rider_id = serializer.validated_data["rider_id"]

        order_item = get_object_or_404(OrderItem, pk=item_id)
        rider = None
        if rider_id is not None:
            rider = User.objects.filter(pk=rider_id, role=User.Role.RIDER).first()
            if rider is None:
                return Response(
                    {"rider_id": ["Rider not found."]}, status=status.HTTP_400_BAD_REQUEST
                )

        try:
            assign_rider(order_item=order_item, rider=rider)
        except AssignmentError as error:
            return Response({"detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)

        order_item = (
            OrderItem.objects.select_related(
                "product", "product__shop", "order", "rider__rider_profile"
            )
            .prefetch_related(
                Prefetch(
                    "status_events",
                    queryset=OrderItemStatusEvent.objects.order_by("changed_at"),
                )
            )
            .get(pk=order_item.pk)
        )
        return Response(AdminOrderItemSerializer(order_item).data)
