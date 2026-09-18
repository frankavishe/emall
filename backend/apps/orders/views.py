from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsCustomer
from apps.orders.models import Order
from apps.orders.serializers import (
    CheckoutSerializer,
    OrderDetailSerializer,
    OrderSerializer,
)
from apps.orders.services import CheckoutError, place_order


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
