from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.orders.models import OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from tests.factories import OrderItemFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _line(shop, status, unit_price="100.00", quantity=1, rate="10.00"):
    subtotal = Decimal(unit_price) * quantity
    commission = subtotal * Decimal(rate) / 100
    return OrderItemFactory(
        product=ProductFactory(shop=shop, is_published=True),
        unit_price=unit_price,
        quantity=quantity,
        commission_rate=rate,
        commission_amount=commission,
        vendor_earning=subtotal - commission,
        status=status,
    )


def test_platform_summary_figures(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    _line(shop, OrderItem.Status.DELIVERED)  # commission 10 earned, 90 available
    _line(shop, OrderItem.Status.SHIPPED, unit_price="50.00")  # 5 pending commission, 45 pending
    _line(shop, OrderItem.Status.CANCELLED, unit_price="1000.00")  # ignored

    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    response = api_client.get("/api/admin/finance/summary")

    assert response.status_code == 200
    data = response.data
    assert data["gross_sales"] == "150.00"
    assert data["commission_earned"] == "10.00"
    assert data["commission_pending"] == "5.00"
    assert data["pending_earnings"] == "45.00"
    assert data["available_balance"] == "90.00"
    assert data["paid_out"] == "0.00"
    assert data["order_count"] == 3


def test_summary_rejects_bad_dates(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    assert api_client.get("/api/admin/finance/summary?from=yesterday").status_code == 400


def test_shop_detail_and_balances(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED, commission_rate="5.00")
    empty_shop = ShopFactory(status=Shop.Status.APPROVED)
    _line(shop, OrderItem.Status.DELIVERED, rate="5.00")

    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    detail = api_client.get(f"/api/admin/shops/{shop.id}").data
    assert detail["owner"]["email"] == shop.owner.email
    assert detail["product_count"] == 1
    assert detail["balance"]["available_balance"] == "95.00"
    assert detail["balance"]["commission_rate"] == "5.00"
    assert detail["balance"]["commission_rate_is_override"] is True

    rows = {row["id"]: row for row in api_client.get("/api/admin/finance/balances").data["results"]}
    assert rows[shop.id]["available_balance"] == "95.00"
    assert rows[shop.id]["commission_rate"] == "5.00"
    assert rows[empty_shop.id]["available_balance"] == "0.00"
    assert rows[empty_shop.id]["commission_rate"] == "10.00"


def test_transactions_and_order_detail(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    line = _line(shop, OrderItem.Status.PENDING)
    PaymentRecord.objects.create(
        order=line.order, method="card", amount="100.00", transaction_reference="ref-123"
    )

    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    transactions = api_client.get("/api/admin/transactions?search=ref-1").data["results"]
    assert len(transactions) == 1
    assert transactions[0]["amount"] == "100.00"
    assert transactions[0]["commission_total"] == "10.00"
    assert transactions[0]["customer"]["email"] == line.order.customer.email

    order = api_client.get(f"/api/admin/orders/{line.order_id}").data
    assert order["payment"]["transaction_reference"] == "ref-123"
    assert order["commission_total"] == "10.00"
    assert order["items"][0]["shop"]["id"] == shop.id


def test_admin_products_include_drafts_and_deleted(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    ProductFactory(shop=shop, is_published=False)
    ProductFactory(shop=shop, is_published=True, is_deleted=True)
    ProductFactory()

    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    assert api_client.get(f"/api/admin/products?shop={shop.id}").data["count"] == 2
    assert api_client.get(f"/api/admin/products?shop={shop.id}&deleted=false").data["count"] == 1


def test_vendor_sees_only_own_earnings_and_payouts(api_client):
    mine = ShopFactory(status=Shop.Status.APPROVED)
    theirs = ShopFactory(status=Shop.Status.APPROVED)
    _line(mine, OrderItem.Status.DELIVERED)
    _line(theirs, OrderItem.Status.DELIVERED, unit_price="500.00")

    owner = mine.owner
    owner.is_vendor = True
    owner.save()
    api_client.force_authenticate(owner)

    earnings = api_client.get("/api/vendor/earnings").data
    assert [row["shop_id"] for row in earnings] == [mine.id]
    assert earnings[0]["available_balance"] == "90.00"
    assert api_client.get(f"/api/vendor/earnings?shop={theirs.id}").data == []
    assert api_client.get("/api/vendor/payouts").data["count"] == 0


def test_vendor_sets_payout_details_only_on_own_shop(api_client):
    mine = ShopFactory()
    theirs = ShopFactory()
    api_client.force_authenticate(mine.owner)
    body = {
        "payout_network": "MPESA",
        "payout_phone": "+255712345678",
        "payout_account_name": "Juma",
    }

    assert api_client.patch(
        f"/api/vendor/shops/{mine.id}/payout-details", body, format="json"
    ).status_code == 200
    mine.refresh_from_db()
    assert mine.has_payout_details
    assert api_client.patch(
        f"/api/vendor/shops/{theirs.id}/payout-details", body, format="json"
    ).status_code == 404
    bad = {**body, "payout_phone": "call me"}
    assert api_client.patch(
        f"/api/vendor/shops/{mine.id}/payout-details", bad, format="json"
    ).status_code == 400


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/admin/finance/summary"),
        ("get", "/api/admin/finance/balances"),
        ("patch", "/api/admin/finance/settings"),
        ("get", "/api/admin/transactions"),
        ("get", "/api/admin/products"),
        ("get", "/api/admin/payouts"),
        ("post", "/api/admin/shops/1/payouts"),
        ("get", "/api/admin/orders/1"),
    ],
)
def test_admin_finance_endpoints_forbid_non_admins(api_client, method, url):
    vendor = ShopFactory().owner
    vendor.is_vendor = True
    vendor.save()
    api_client.force_authenticate(vendor)
    assert getattr(api_client, method)(url).status_code == 403
