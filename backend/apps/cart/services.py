"""Which cart a request is working on: a Customer's own cart, or an anonymous guest's cart found
through the httpOnly guest-cart cookie (guest checkout)."""

import secrets

from django.conf import settings
from django.db import transaction

from apps.cart.models import Cart, CartItem


def _guest_token_from(request):
    return request.COOKIES.get(settings.GUEST_CART_COOKIE_NAME) or None


def resolve_cart(request, *, create):
    """Returns the requester's cart, or `None` when there is none yet and `create` is false.

    A newly created guest cart is flagged with `cart.new_guest_token` so the view knows to set
    the cookie on its response (see `attach_guest_cookie`)."""

    user = request.user
    if user and user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(customer=user)
            return cart
        return Cart.objects.filter(customer=user).first()

    token = _guest_token_from(request)
    if token:
        cart = Cart.objects.filter(guest_token=token).first()
        if cart is not None:
            return cart
    if not create:
        return None
    cart = Cart.objects.create(guest_token=secrets.token_urlsafe(32))
    cart.new_guest_token = cart.guest_token
    return cart


def attach_guest_cookie(response, cart):
    """Sets (or refreshes) the guest-cart cookie for a guest cart; a no-op for a Customer's."""

    if cart is None or cart.guest_token is None:
        return response
    response.set_cookie(
        settings.GUEST_CART_COOKIE_NAME,
        cart.guest_token,
        max_age=settings.GUEST_CART_COOKIE_MAX_AGE,
        path=settings.GUEST_CART_COOKIE_PATH,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        httponly=True,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    return response


def clear_guest_cookie(response):
    response.delete_cookie(
        settings.GUEST_CART_COOKIE_NAME,
        path=settings.GUEST_CART_COOKIE_PATH,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    return response


def merge_guest_cart(request, user, response):
    """On sign-in, moves the guest cart's lines into the Customer's own cart (adding quantities
    to a line that's already there, capped at current stock), then deletes the guest cart and
    its cookie. Non-Customer accounts simply have the guest cart left alone."""

    token = _guest_token_from(request)
    if not token or not user.has_role("CUSTOMER"):
        return response

    with transaction.atomic():
        guest_cart = Cart.objects.select_for_update().filter(guest_token=token).first()
        if guest_cart is None:
            return clear_guest_cookie(response)
        # A guest cart whose checkout is still awaiting payment has to stay put: the payment
        # callback clears it by its token once the payment succeeds.
        if _has_pending_payment(token):
            return response

        cart, _ = Cart.objects.get_or_create(customer=user)
        for guest_item in guest_cart.items.select_related("product"):
            available = guest_item.product.stock_quantity or 0
            item = CartItem.objects.filter(cart=cart, product=guest_item.product).first()
            if item is None:
                quantity = min(guest_item.quantity, available)
                if quantity > 0:
                    CartItem.objects.create(
                        cart=cart, product=guest_item.product, quantity=quantity
                    )
            else:
                merged = min(item.quantity + guest_item.quantity, max(available, item.quantity))
                if merged != item.quantity:
                    item.quantity = merged
                    item.save(update_fields=["quantity"])
        guest_cart.delete()

    return clear_guest_cookie(response)


def _has_pending_payment(token):
    from apps.orders.models import Order

    return Order.objects.filter(
        guest_cart_token=token, status=Order.Status.AWAITING_PAYMENT
    ).exists()
