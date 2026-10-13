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
from apps.cart.services import attach_guest_cookie, resolve_cart
from apps.core.permissions import IsCustomerOrGuest
from apps.core.throttles import GuestScopedRateThrottle


class _CartView(APIView):
    """Open to Customers and anonymous guests (guest checkout); a guest's cart is found through
    the httpOnly guest-cart cookie."""

    permission_classes = [IsCustomerOrGuest]
    throttle_classes = [GuestScopedRateThrottle]
    throttle_scope = "guest_cart"


class CartDetailView(_CartView):
    """Creates a Customer's cart lazily on first access (research.md §1, FR-002). A guest's cart
    is only created by their first add, so merely viewing the cart page leaves no rows behind."""

    def get(self, request):
        cart = resolve_cart(request, create=request.user.is_authenticated)
        if cart is None:
            return Response({"id": None, "items": [], "total": "0.00"})
        cart = Cart.objects.prefetch_related("items__product__shop").get(pk=cart.pk)
        return attach_guest_cookie(Response(CartSerializer(cart).data), cart)


class CartItemCreateView(_CartView):
    """Adding an already-present product merges into that line's quantity instead of creating a
    second row (FR-005, research.md §3) — the combined quantity is re-validated against current
    stock even though the individual request quantity already passed serializer validation."""

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart = resolve_cart(request, create=True)
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
        response = Response(CartItemSerializer(item).data, status=response_status)
        return attach_guest_cookie(response, cart)


class CartItemDetailView(_CartView):
    """Scoped to the requester's own cart at the queryset level, so another Customer's (or
    guest's) line ID 404s rather than 403ing (FR-018, research.md §6)."""

    def get_object(self, request, item_id):
        cart = resolve_cart(request, create=False)
        return get_object_or_404(CartItem, pk=item_id, cart=cart)

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
