"""Who can act on a services shop (Constitution Principle II). Someone else's shop reads as not
found; the owner's own shop that isn't an approved services shop is refused with the reason."""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.vendors.models import Shop

NOT_APPROVED = "This shop must be approved by an administrator first."
NOT_SERVICES = "This shop sells goods, so it can't list services or take bookings."


def require_bookable_shop(shop):
    """The approval gate for every change to a shop's services and schedule."""

    if shop.business_type != Shop.BusinessType.SERVICES:
        raise PermissionDenied(NOT_SERVICES)
    if shop.status != Shop.Status.APPROVED:
        raise PermissionDenied(NOT_APPROVED)


def owned_shop(request, shop_id):
    return get_object_or_404(Shop, pk=shop_id, owner=request.user)


def owned_services_shop(request, shop_id):
    """The owner's services shop, in any approval state (for reading)."""

    shop = owned_shop(request, shop_id)
    if shop.business_type != Shop.BusinessType.SERVICES:
        raise PermissionDenied(NOT_SERVICES)
    return shop


def owned_bookable_shop(request, shop_id):
    shop = owned_shop(request, shop_id)
    require_bookable_shop(shop)
    return shop
