from decimal import Decimal

import pytest

from apps.delivery.pricing import DeliveryError, haversine_km, leg_fee, quote_delivery
from apps.finance.models import PlatformSettings
from tests.factories import ShopFactory

pytestmark = pytest.mark.django_db

# Dar es Salaam city centre and Bagamoyo (~60 km straight-line apart).
DAR = (Decimal("-6.792400"), Decimal("39.208300"))
BAGAMOYO = (Decimal("-6.442200"), Decimal("38.904200"))


def test_haversine_zero_and_known_distance():
    assert haversine_km(*DAR, *DAR) == 0
    # One degree of latitude is ~111.2 km.
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.05)


def test_leg_fee_applies_minimum_and_rounds_up_to_100():
    settings = PlatformSettings.get_solo()  # defaults: base 2000, 500/km, min 2000, factor 1.30
    assert leg_fee(Decimal("0"), settings) == Decimal("2000.00")
    # 2000 + 500 * 3.21 * 1.30 = 4086.5 -> 4100
    assert leg_fee(Decimal("3.21"), settings) == Decimal("4100.00")
    # exactly on a step stays put: 2000 + 500 * 2 * 1.30 = 3300
    assert leg_fee(Decimal("2"), settings) == Decimal("3300.00")


def test_minimum_fee_wins_when_formula_is_lower():
    settings = PlatformSettings.get_solo()
    settings.delivery_base_fee = Decimal("0")
    settings.delivery_min_fee = Decimal("1500")
    assert leg_fee(Decimal("1"), settings) == Decimal("1500.00")


def test_quote_one_leg_per_distinct_shop():
    near = ShopFactory(latitude=DAR[0], longitude=DAR[1])
    other = ShopFactory(latitude=Decimal("-6.800000"), longitude=Decimal("39.250000"))

    legs = quote_delivery([near, other, near], *DAR)

    assert [leg.shop for leg in legs] == [near, other]
    assert legs[0].distance_km == Decimal("0.00")
    assert legs[0].fee == Decimal("2000.00")
    assert legs[1].distance_km > 0
    assert legs[1].fee > legs[0].fee


def test_quote_rejects_shop_without_location():
    shop = ShopFactory(name="Nowhere Shop", latitude=None, longitude=None)

    with pytest.raises(DeliveryError) as exc:
        quote_delivery([shop], *DAR)

    assert exc.value.code == "shop_without_location"
    assert "Nowhere Shop" in exc.value.detail


def test_quote_rejects_beyond_max_distance_but_accepts_within():
    shop = ShopFactory(name="Dar Shop", latitude=DAR[0], longitude=DAR[1])

    with pytest.raises(DeliveryError) as exc:
        quote_delivery([shop], *BAGAMOYO)
    assert exc.value.code == "out_of_range"
    assert "Dar Shop" in exc.value.detail

    settings = PlatformSettings.get_solo()
    settings.delivery_max_distance_km = Decimal("100")
    settings.save()
    [leg] = quote_delivery([shop], *BAGAMOYO)
    assert Decimal("50") < leg.distance_km < Decimal("100")
