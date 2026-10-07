from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.finance import disbursement
from apps.finance.models import Payout
from apps.orders.models import OrderItem
from apps.vendors.models import Shop
from tests.factories import OrderItemFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _shop_with_payout_details(phone="+255712345678"):
    return ShopFactory(
        status=Shop.Status.APPROVED,
        payout_network=Shop.PayoutNetwork.MPESA,
        payout_phone=phone,
        payout_account_name="Juma Shop",
    )


def _line(shop, status=OrderItem.Status.DELIVERED, earning="90.00", commission="10.00"):
    return OrderItemFactory(
        product=ProductFactory(shop=shop, is_published=True),
        unit_price=Decimal(earning) + Decimal(commission),
        commission_rate="10.00",
        commission_amount=commission,
        vendor_earning=earning,
        status=status,
    )


@pytest.fixture
def admin_client(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    return api_client


def test_payout_pays_only_delivered_unpaid_lines(admin_client):
    shop = _shop_with_payout_details()
    delivered_a = _line(shop, earning="90.00")
    delivered_b = _line(shop, earning="45.00", commission="5.00")
    shipped = _line(shop, status=OrderItem.Status.SHIPPED)
    cancelled = _line(shop, status=OrderItem.Status.CANCELLED)
    other_shop_line = _line(_shop_with_payout_details())

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 201
    assert response.data["status"] == "SUCCEEDED"
    assert response.data["amount"] == "135.00"
    assert response.data["phone"] == "+255712345678"
    assert response.data["provider_reference"]
    payout = Payout.objects.get(pk=response.data["id"])
    assert set(payout.items.values_list("id", flat=True)) == {delivered_a.id, delivered_b.id}
    for line in (shipped, cancelled, other_shop_line):
        line.refresh_from_db()
        assert line.payout_id is None


def test_second_payout_has_nothing_to_pay(admin_client):
    shop = _shop_with_payout_details()
    _line(shop)
    assert admin_client.post(f"/api/admin/shops/{shop.id}/payouts").status_code == 201

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 400
    assert Payout.objects.count() == 1


def test_payout_refused_without_payout_details(admin_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    _line(shop)

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 400
    assert "payout details" in response.data["detail"]
    assert Payout.objects.count() == 0


def test_failed_disbursement_releases_lines_and_retry_succeeds(admin_client):
    shop = _shop_with_payout_details(phone=disbursement.MOCK_FAILING_PHONE)
    line = _line(shop)

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 201
    assert response.data["status"] == "FAILED"
    assert response.data["failure_reason"]
    line.refresh_from_db()
    assert line.payout_id is None

    balances = admin_client.get("/api/admin/finance/balances").data["results"]
    assert balances[0]["available_balance"] == "90.00"

    shop.payout_phone = "+255712345678"
    shop.save()
    response = admin_client.post(f"/api/admin/payouts/{response.data['id']}/retry")

    assert response.status_code == 200
    assert response.data["status"] == "SUCCEEDED"
    assert response.data["phone"] == "+255712345678"
    line.refresh_from_db()
    assert line.payout_id == response.data["id"]


def test_only_failed_payouts_can_be_retried(admin_client):
    shop = _shop_with_payout_details()
    _line(shop)
    payout_id = admin_client.post(f"/api/admin/shops/{shop.id}/payouts").data["id"]

    response = admin_client.post(f"/api/admin/payouts/{payout_id}/retry")

    assert response.status_code == 400


def test_provider_crash_is_recorded_as_failed(admin_client, monkeypatch):
    class Exploding(disbursement.DisbursementService):
        def disburse(self, **kwargs):
            raise RuntimeError("timeout")

    monkeypatch.setattr(disbursement, "get_disbursement_service", lambda: Exploding())
    shop = _shop_with_payout_details()
    line = _line(shop)

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.data["status"] == "FAILED"
    assert "timeout" in response.data["failure_reason"]
    line.refresh_from_db()
    assert line.payout_id is None


def test_payout_detail_lists_lines(admin_client):
    shop = _shop_with_payout_details()
    line = _line(shop)
    payout_id = admin_client.post(f"/api/admin/shops/{shop.id}/payouts").data["id"]

    response = admin_client.get(f"/api/admin/payouts/{payout_id}")

    assert response.status_code == 200
    assert response.data["line_count"] == 1
    assert [item["id"] for item in response.data["items"]] == [line.id]
    assert admin_client.get(f"/api/admin/payouts?shop={shop.id}").data["count"] == 1
