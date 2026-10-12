"""Delivery pricing (007-delivery-fee). Pure math over `PlatformSettings` and shop locations, so
it's shared by the checkout quote endpoint and `orders.services.place_order()`, which always
recomputes it server-side rather than trusting a client-sent fee.

Each distinct shop in an order is one delivery leg:
    fee = max(min_fee, base_fee + per_km_fee * distance_km * road_factor)
rounded up to the nearest TZS 100, where `distance_km` is the straight-line (great-circle)
distance from the shop's location to the customer's pin.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from apps.finance.models import PlatformSettings

EARTH_RADIUS_KM = 6371.0088
FEE_STEP = Decimal("100")


class DeliveryError(Exception):
    """Raised when an order can't be delivered: a shop without a location, or a pin beyond the
    maximum delivery distance from a shop."""

    def __init__(self, code, detail, shop=None):
        self.code = code
        self.detail = detail
        self.shop = shop
        super().__init__(detail)


@dataclass(frozen=True)
class DeliveryLeg:
    shop: object
    distance_km: Decimal
    fee: Decimal


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance between two points in kilometres."""

    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = phi2 - phi1
    dlmb = math.radians(float(lng2) - float(lng1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def leg_fee(distance_km, settings):
    raw = (
        settings.delivery_base_fee
        + settings.delivery_per_km_fee * distance_km * settings.delivery_road_factor
    )
    fee = max(settings.delivery_min_fee, raw)
    return ((fee / FEE_STEP).to_integral_value(rounding=ROUND_CEILING) * FEE_STEP).quantize(
        Decimal("0.01")
    )


def quote_delivery(shops, latitude, longitude, settings=None):
    """One `DeliveryLeg` per distinct shop in `shops` (in the given order), or `DeliveryError`
    if any shop can't deliver to (`latitude`, `longitude`)."""

    settings = settings or PlatformSettings.get_solo()
    legs = []
    seen = set()
    for shop in shops:
        if shop.id in seen:
            continue
        seen.add(shop.id)
        if not shop.has_location:
            raise DeliveryError(
                "shop_without_location",
                f"{shop.name} hasn't set its delivery location yet, so its products can't be "
                "delivered. Remove them from your cart to continue.",
                shop=shop,
            )
        distance = Decimal(
            str(haversine_km(shop.latitude, shop.longitude, latitude, longitude))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if distance > settings.delivery_max_distance_km:
            raise DeliveryError(
                "out_of_range",
                f"Your location is {distance} km from {shop.name}, beyond the "
                f"{settings.delivery_max_distance_km.normalize():f} km delivery area.",
                shop=shop,
            )
        legs.append(DeliveryLeg(shop=shop, distance_km=distance, fee=leg_fee(distance, settings)))
    return legs
