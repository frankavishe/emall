"""007-delivery-fee: mandatory delivery pin, per-shop fees computed server-side, quote endpoint."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.finance.models import PlatformSettings
from apps.orders.models import Order, OrderDelivery
from apps.payments.models import PaymentRecord
from tests.factories import (
    CartFactory,
    CartItemFactory,
    ProductFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

PIN = {"latitude": -6.7924, "longitude": 39.2083}  # Dar es Salaam centre (ShopFactory default)
SHIPPING = {
    "recipient_name": "Neema Juma",
    "address_line": "Plot 12, Samora Avenue",
    "city": "Dar es Salaam",
    "region": "Dar es Salaam",
    "postal_code": "11101",
    "country": "Tanzania",
    "phone": "+255712345678",
    **PIN,
}


def _customer_with_cart(api_client, *products):
    customer = UserFactory(role=User.Role.CUSTOMER)
    cart = CartFactory(customer=customer)
    for product in products:
        CartItemFactory(cart=cart, product=product, quantity=1)
    api_client.force_authenticate(customer)
    return customer


def _checkout(api_client, shipping=SHIPPING, **extra):
    return api_client.post(
        "/api/checkout", {"shipping": shipping, "payment_method": "card", **extra}, format="json"
    )


def test_checkout_without_pin_is_rejected(api_client):
    product = ProductFactory(is_published=True, price="5000.00")
    _customer_with_cart(api_client, product)
    shipping = {k: v for k, v in SHIPPING.items() if k not in ("latitude", "longitude")}

    response = _checkout(api_client, shipping)

    assert response.status_code == 400
    assert "latitude" in response.data["shipping"]
    assert "longitude" in response.data["shipping"]
    assert not Order.objects.exists()


@pytest.mark.parametrize("lat,lng", [(91, 39), (-6, 181), ("abc", 39)])
def test_checkout_rejects_invalid_coordinates(api_client, lat, lng):
    _customer_with_cart(api_client, ProductFactory(is_published=True))

    response = _checkout(api_client, {**SHIPPING, "latitude": lat, "longitude": lng})

    assert response.status_code == 400
    assert not Order.objects.exists()


def test_two_shops_two_legs_fees_summed_and_charged(api_client):
    near = ShopFactory(status="APPROVED")
    # ~4.8 km east of the pin.
    far = ShopFactory(status="APPROVED", longitude=Decimal("39.252000"))
    p1 = ProductFactory(shop=near, is_published=True, price="10000.00")
    p2 = ProductFactory(shop=far, is_published=True, price="3000.00")
    p3 = ProductFactory(shop=near, is_published=True, price="1000.00")
    _customer_with_cart(api_client, p1, p2, p3)

    response = _checkout(api_client)

    assert response.status_code == 201
    order = Order.objects.get()
    legs = {leg.shop_id: leg for leg in OrderDelivery.objects.filter(order=order)}
    assert set(legs) == {near.id, far.id}  # one leg per shop, not per item
    assert legs[near.id].fee == Decimal("2000.00")
    far_leg = legs[far.id]
    assert Decimal("4.7") < far_leg.distance_km < Decimal("4.9")
    # 2000 + 500 * ~4.82 * 1.30 = ~5133 -> rounded up to a multiple of 100.
    assert far_leg.fee % 100 == 0
    assert Decimal("5100") <= far_leg.fee <= Decimal("5200")

    expected_fee = legs[near.id].fee + far_leg.fee
    assert order.delivery_fee == expected_fee
    assert order.latitude == Decimal("-6.792400")
    assert response.data["delivery_fee"] == str(expected_fee)
    assert response.data["items_subtotal"] == "14000.00"
    assert PaymentRecord.objects.get().amount == Decimal("14000.00") + expected_fee
    assert len(response.data["deliveries"]) == 2


def test_client_sent_fee_is_ignored(api_client):
    _customer_with_cart(api_client, ProductFactory(is_published=True, price="1000.00"))

    response = _checkout(
        api_client, {**SHIPPING, "delivery_fee": "0.00"}, delivery_fee="0.00", total="1.00"
    )

    assert response.status_code == 201
    assert Order.objects.get().delivery_fee == Decimal("2000.00")
    assert PaymentRecord.objects.get().amount == Decimal("3000.00")


def test_shop_without_location_blocks_checkout(api_client):
    shop = ShopFactory(status="APPROVED", name="Kariakoo Traders", latitude=None, longitude=None)
    product = ProductFactory(shop=shop, is_published=True, stock_quantity=4)
    _customer_with_cart(api_client, product)

    response = _checkout(api_client)

    assert response.status_code == 400
    assert response.data["code"] == "shop_without_location"
    assert "Kariakoo Traders" in response.data["detail"]
    assert not Order.objects.exists()
    assert not PaymentRecord.objects.exists()
    product.refresh_from_db()
    assert product.stock_quantity == 4


def test_out_of_range_blocks_checkout(api_client):
    settings = PlatformSettings.get_solo()
    settings.delivery_max_distance_km = Decimal("3")
    settings.save()
    shop = ShopFactory(status="APPROVED", name="Far Shop", longitude=Decimal("39.252000"))
    _customer_with_cart(api_client, ProductFactory(shop=shop, is_published=True))

    response = _checkout(api_client)

    assert response.status_code == 400
    assert response.data["code"] == "out_of_range"
    assert "Far Shop" in response.data["detail"]
    assert not Order.objects.exists()


def test_settings_change_applies_to_next_checkout(api_client):
    settings = PlatformSettings.get_solo()
    settings.delivery_min_fee = Decimal("3500")
    settings.save()
    _customer_with_cart(api_client, ProductFactory(is_published=True, price="1000.00"))

    response = _checkout(api_client)

    assert response.status_code == 201
    assert response.data["delivery_fee"] == "3500.00"


# --- quote endpoint -------------------------------------------------------------------------


def test_quote_returns_legs_and_totals_without_creating_an_order(api_client):
    shop = ShopFactory(status="APPROVED", name="Mlimani Books")
    _customer_with_cart(
        api_client,
        ProductFactory(shop=shop, is_published=True, price="1500.00"),
        ProductFactory(shop=shop, is_published=True, price="500.00"),
    )

    response = api_client.post("/api/checkout/delivery-quote", PIN, format="json")

    assert response.status_code == 200
    assert response.data == {
        "legs": [
            {
                "shop_id": shop.id,
                "shop_name": "Mlimani Books",
                "distance_km": "0.00",
                "fee": "2000.00",
            }
        ],
        "items_subtotal": "2000.00",
        "delivery_fee": "2000.00",
        "total": "4000.00",
    }
    assert not Order.objects.exists()


def test_quote_errors_carry_codes(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.CUSTOMER))
    response = api_client.post("/api/checkout/delivery-quote", PIN, format="json")
    assert response.status_code == 400
    assert response.data["code"] == "empty_cart"

    shop = ShopFactory(status="APPROVED", latitude=None, longitude=None)
    _customer_with_cart(api_client, ProductFactory(shop=shop, is_published=True))
    response = api_client.post("/api/checkout/delivery-quote", PIN, format="json")
    assert response.status_code == 400
    assert response.data["code"] == "shop_without_location"


def test_quote_requires_valid_pin_and_customer(api_client):
    _customer_with_cart(api_client, ProductFactory(is_published=True))
    response = api_client.post("/api/checkout/delivery-quote", {"latitude": 100}, format="json")
    assert response.status_code == 400
    assert "longitude" in response.data

    api_client.force_authenticate(None)
    response = api_client.post("/api/checkout/delivery-quote", PIN, format="json")
    assert response.status_code == 401


def test_legacy_order_without_delivery_still_renders(api_client):
    from tests.factories import OrderItemFactory

    item = OrderItemFactory(unit_price="100.00", quantity=2)
    api_client.force_authenticate(item.order.customer)

    response = api_client.get(f"/api/orders/{item.order.id}")

    assert response.status_code == 200
    assert response.data["delivery_fee"] == "0.00"
    assert response.data["total"] == "200.00"
    assert response.data["deliveries"] == []
    assert response.data["shipping"]["latitude"] is None
