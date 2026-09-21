from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsCustomer, IsVendor
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import (
    CheckoutSerializer,
    OrderDetailSerializer,
    OrderItemStatusUpdateSerializer,
    OrderSerializer,
    VendorOrderItemSerializer,
)
from apps.orders.services import CheckoutError, TransitionError, advance_order_item_status, place_order
from apps.vendors.models import Shop


class CheckoutView(APIView):
    """Re-validates the cart, charges the mock payment service, and — only if both succeed —
    creates the Order atomically (research.md §4). Every failure case is translated to the `400`
    response shapes in contracts/cart-checkout-api.md."""

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = place_order(
                customer=request.user,
                shipping_data=serializer.validated_data["shipping"],
                payment_method=serializer.validated_data["payment_method"],
            )
        except CheckoutError as error:
            body = {"detail": error.detail, **error.extra}
            if error.code == "payment_failed":
                body["code"] = error.code
            return Response(body, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)


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


class VendorOrderItemListView(ListAPIView):
    """Lists only order lines whose product belongs to one of the requester's own shops, across
    every Customer's order (FR-001, FR-004)."""

    permission_classes = [IsVendor]
    serializer_class = VendorOrderItemSerializer

    def get_queryset(self):
        return (
            OrderItem.objects.filter(product__shop__owner=self.request.user)
            .select_related("product", "product__shop", "order")
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
