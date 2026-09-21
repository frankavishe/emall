from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart, CartItem
from apps.cart.serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
)
from apps.core.permissions import IsCustomer


class CartDetailView(APIView):
    """Creates the Customer's cart lazily on first access (research.md §1, FR-002)."""

    permission_classes = [IsCustomer]

    def get(self, request):
        Cart.objects.get_or_create(customer=request.user)
        cart = Cart.objects.prefetch_related("items__product__shop").get(
            customer=request.user
        )
        return Response(CartSerializer(cart).data)


class CartItemCreateView(APIView):
    """Adding an already-present product merges into that line's quantity instead of creating a
    second row (FR-005, research.md §3) — the combined quantity is re-validated against current
    stock even though the individual request quantity already passed serializer validation."""

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart, _ = Cart.objects.get_or_create(customer=request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )
        if not created:
            combined_quantity = item.quantity + quantity
            available = product.stock_quantity or 0
            if combined_quantity > available:
                raise ValidationError({"quantity": f"Only {available} available."})
            item.quantity = combined_quantity
            item.save(update_fields=["quantity"])

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(CartItemSerializer(item).data, status=response_status)


class CartItemDetailView(APIView):
    """Scoped to the requester's own cart at the queryset level, so another Customer's line ID
    404s rather than 403ing (FR-018, research.md §6)."""

    permission_classes = [IsCustomer]

    def get_object(self, request, item_id):
        return get_object_or_404(CartItem, pk=item_id, cart__customer=request.user)

    def patch(self, request, item_id):
        item = self.get_object(request, item_id)
        serializer = CartItemUpdateSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request, item_id):
        item = self.get_object(request, item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
