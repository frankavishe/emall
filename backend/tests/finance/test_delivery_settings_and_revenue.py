"""007-delivery-fee: admin delivery pricing settings, delivery revenue, shop locations."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.finance.models import PlatformSettings
from apps.vendors.models import Shop
from tests.factories import OrderFactory, OrderItemFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

SETTINGS_URL = "/api/admin/finance/settings"


def _admin(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))


def test_admin_reads_and_partially_updates_delivery_pricing(api_client):
    _admin(api_client)

    data = api_client.get(SETTINGS_URL).data
    assert data["delivery_base_fee"] == "2000.00"
    assert data["delivery_per_km_fee"] == "500.00"
    assert data["delivery_min_fee"] == "2000.00"
    assert data["delivery_max_distance_km"] == "50.00"
    assert data["delivery_road_factor"] == "1.30"

    response = api_client.patch(
        SETTINGS_URL, {"delivery_per_km_fee": "750", "delivery_road_factor": "1.5"}, format="json"
    )

    assert response.status_code == 200
    settings = PlatformSettings.get_solo()
    assert settings.delivery_per_km_fee == Decimal("750.00")
    assert settings.delivery_road_factor == Decimal("1.50")
    # Untouched fields keep their values.
    assert settings.delivery_base_fee == Decimal("2000.00")
    assert settings.default_commission_rate == Decimal("10.00")


@pytest.mark.parametrize(
    "field,value",
    [
        ("delivery_base_fee", "-1"),
        ("delivery_per_km_fee", "-0.01"),
        ("delivery_min_fee", "-5"),
        ("delivery_max_distance_km", "0"),
        ("delivery_road_factor", "0.9"),
    ],
)
def test_invalid_delivery_pricing_is_rejected(api_client, field, value):
    _admin(api_client)

    response = api_client.patch(SETTINGS_URL, {field: value}, format="json")

    assert response.status_code == 400
    assert field in response.data


def test_non_admin_cannot_change_delivery_pricing(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.CUSTOMER))
    response = api_client.patch(SETTINGS_URL, {"delivery_base_fee": "0"}, format="json")
    assert response.status_code == 403
    assert PlatformSettings.get_solo().delivery_base_fee == Decimal("2000.00")


def test_summary_shows_delivery_revenue_separately_from_shop_figures(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    for fee in ("2000.00", "3500.00"):
        OrderItemFactory(
            order=OrderFactory(delivery_fee=fee),
            product__shop=shop,
            unit_price="100.00",
            commission_amount="10.00",
            vendor_earning="90.00",
        )
    _admin(api_client)

    data = api_client.get("/api/admin/finance/summary").data

    assert data["delivery_revenue"] == "5500.00"
    assert data["gross_sales"] == "200.00"
    assert data["available_balance"] == "180.00"


# --- shop locations -------------------------------------------------------------------------

LOCATION = {"latitude": -6.8160837123, "longitude": 39.2803583, "location_address": "Kariakoo"}


def test_owner_sets_shop_location(api_client):
    shop = ShopFactory(latitude=None, longitude=None)
    api_client.force_authenticate(shop.owner)

    response = api_client.put(f"/api/vendor/shops/{shop.id}/location", LOCATION, format="json")

    assert response.status_code == 200
    assert response.data["latitude"] == "-6.816084"
    assert response.data["location_address"] == "Kariakoo"
    shop.refresh_from_db()
    assert shop.has_location
    assert shop.longitude == Decimal("39.280358")


def test_other_vendor_cannot_set_shop_location(api_client):
    shop = ShopFactory(latitude=None, longitude=None)
    api_client.force_authenticate(UserFactory(role=User.Role.VENDOR))

    response = api_client.put(f"/api/vendor/shops/{shop.id}/location", LOCATION, format="json")

    assert response.status_code == 404
    shop.refresh_from_db()
    assert not shop.has_location


def test_shop_location_validation(api_client):
    shop = ShopFactory()
    api_client.force_authenticate(shop.owner)

    response = api_client.put(
        f"/api/vendor/shops/{shop.id}/location",
        {"latitude": 95, "longitude": 39, "location_address": ""},
        format="json",
    )

    assert response.status_code == 400
    assert "latitude" in response.data
    assert "location_address" in response.data


def test_admin_sets_any_shop_location_and_sees_it_in_detail(api_client):
    shop = ShopFactory(latitude=None, longitude=None)
    _admin(api_client)

    response = api_client.put(f"/api/admin/shops/{shop.id}/location", LOCATION, format="json")
    assert response.status_code == 200

    detail = api_client.get(f"/api/admin/shops/{shop.id}").data
    assert detail["latitude"] == "-6.816084"
    assert detail["location_address"] == "Kariakoo"


def test_customer_cannot_use_admin_location_endpoint(api_client):
    shop = ShopFactory()
    api_client.force_authenticate(UserFactory(role=User.Role.CUSTOMER))
    response = api_client.put(f"/api/admin/shops/{shop.id}/location", LOCATION, format="json")
    assert response.status_code == 403
