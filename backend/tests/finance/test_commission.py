from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.finance.models import PlatformSettings
from apps.finance.services import split_line
from apps.orders.models import OrderItem
from apps.payments.models import PaymentRecord
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Dar es Salaam",
    "region": "Dar es Salaam",
    "postal_code": "11101",
    "country": "Tanzania",
    "phone": "+255712345678",
}


def _checkout(api_client, customer, *products):
    api_client.force_authenticate(customer)
    for product, quantity in products:
        api_client.post(
            "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
        )
    return api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )


@pytest.mark.parametrize(
    ("subtotal", "rate", "commission", "earning"),
    [
        ("100.00", "10", "10.00", "90.00"),
        ("9.99", "10", "1.00", "8.99"),
        ("9.99", "12.5", "1.25", "8.74"),
        ("50.00", "0", "0.00", "50.00"),
        ("50.00", "100", "50.00", "0.00"),
    ],
)
def test_split_line_rounds_half_up_and_sums_to_subtotal(subtotal, rate, commission, earning):
    got_commission, got_earning = split_line(Decimal(subtotal), Decimal(rate))
    assert got_commission == Decimal(commission)
    assert got_earning == Decimal(earning)
    assert got_commission + got_earning == Decimal(subtotal)


def test_checkout_freezes_default_and_override_rates_and_records_amount(api_client):
    settings = PlatformSettings.get_solo()
    settings.default_commission_rate = Decimal("10.00")
    settings.save()
    default_product = ProductFactory(is_published=True, price="100.00", stock_quantity=5)
    override_product = ProductFactory(is_published=True, price="200.00", stock_quantity=5)
    override_product.shop.commission_rate = Decimal("5.00")
    override_product.shop.save()

    response = _checkout(
        api_client,
        UserFactory(role=User.Role.CUSTOMER),
        (default_product, 2),
        (override_product, 1),
    )

    assert response.status_code == 201
    assert response.data["payment"]["amount"] == "400.00"
    default_line = OrderItem.objects.get(product=default_product)
    assert default_line.commission_rate == Decimal("10.00")
    assert default_line.commission_amount == Decimal("20.00")
    assert default_line.vendor_earning == Decimal("180.00")
    override_line = OrderItem.objects.get(product=override_product)
    assert override_line.commission_rate == Decimal("5.00")
    assert override_line.commission_amount == Decimal("10.00")
    assert override_line.vendor_earning == Decimal("190.00")
    assert PaymentRecord.objects.get().amount == Decimal("400.00")


def test_changing_rate_later_does_not_touch_existing_lines(api_client):
    product = ProductFactory(is_published=True, price="100.00", stock_quantity=5)
    _checkout(api_client, UserFactory(role=User.Role.CUSTOMER), (product, 1))

    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    api_client.force_authenticate(admin)
    response = api_client.patch(
        "/api/admin/finance/settings", {"default_commission_rate": "25"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["default_commission_rate"] == "25.00"
    assert OrderItem.objects.get().commission_amount == Decimal("10.00")


def test_admin_sets_and_clears_shop_override(api_client):
    product = ProductFactory()
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))

    response = api_client.patch(
        f"/api/admin/shops/{product.shop_id}/commission",
        {"commission_rate": "7.5"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["effective_commission_rate"] == Decimal("7.50")

    response = api_client.patch(
        f"/api/admin/shops/{product.shop_id}/commission",
        {"commission_rate": None},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["commission_rate"] is None
    assert response.data["effective_commission_rate"] == Decimal("10.00")


@pytest.mark.parametrize("rate", ["-1", "100.01", "abc"])
def test_invalid_rates_are_rejected(api_client, rate):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    response = api_client.patch(
        "/api/admin/finance/settings", {"default_commission_rate": rate}, format="json"
    )
    assert response.status_code == 400
    assert PlatformSettings.get_solo().default_commission_rate == Decimal("10.00")
