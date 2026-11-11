"""US4: completed and no-show bookings flow into shop balances, payouts and mall figures next to
goods lines, without multiplying either side (research.md section 9, FR-030)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.finance import disbursement
from apps.finance.models import Payout
from apps.finance.services import platform_summary, shop_balance, shops_with_balances
from apps.orders.models import OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from tests.factories import (
    BookingFactory,
    OrderItemFactory,
    ProductFactory,
    ServiceFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

FIGURES = (
    "gross_sales",
    "commission_earned",
    "commission_pending",
    "pending_earnings",
    "available_balance",
    "in_payout",
    "paid_out",
)


def _shop(phone="+255712345678"):
    return ShopFactory(
        status=Shop.Status.APPROVED,
        payout_network=Shop.PayoutNetwork.MPESA,
        payout_phone=phone,
        payout_account_name="Juma Shop",
    )


def _line(shop, status=OrderItem.Status.DELIVERED, unit_price="100.00"):
    subtotal = Decimal(unit_price)
    commission = subtotal / 10
    return OrderItemFactory(
        product=ProductFactory(shop=shop, is_published=True),
        unit_price=unit_price,
        commission_rate="10.00",
        commission_amount=commission,
        vendor_earning=subtotal - commission,
        status=status,
    )


def _booking(shop, status, **fields):
    """A 200.00 booking: 20.00 commission, 180.00 earning."""

    now = timezone.now()
    paid = status not in (Booking.Status.REQUESTED, Booking.Status.AWAITING_PAYMENT)
    return BookingFactory(
        service=ServiceFactory(shop=shop, price=Decimal("200.00")),
        status=status,
        starts_at=now - timedelta(hours=1),
        respond_by=now - timedelta(days=2),
        confirmed_at=now - timedelta(days=1) if paid else None,
        completed_at=now
        if status in (Booking.Status.COMPLETED, Booking.Status.NO_SHOW)
        else None,
        **fields,
    )


def _mixed_shop(phone="+255712345678"):
    """Goods: 2 delivered lines (90 + 90 available) and 1 shipped (45 pending).
    Bookings: 2 completed and 1 no-show (540 available), 1 confirmed (180 pending), and 1
    cancelled, which adds nothing."""

    shop = _shop(phone)
    _line(shop)
    _line(shop)
    _line(shop, OrderItem.Status.SHIPPED, unit_price="50.00")
    _booking(shop, Booking.Status.COMPLETED)
    _booking(shop, Booking.Status.COMPLETED)
    _booking(shop, Booking.Status.NO_SHOW)
    _booking(shop, Booking.Status.CONFIRMED)
    _booking(shop, Booking.Status.CANCELLED)
    return shop


EXPECTED = {
    "gross_sales": Decimal("1050.00"),  # 250 goods + 4 x 200 bookings
    "commission_earned": Decimal("80.00"),  # 20 + 60
    "commission_pending": Decimal("25.00"),  # 5 + 20
    "pending_earnings": Decimal("225.00"),  # 45 + 180
    "available_balance": Decimal("720.00"),  # 180 + 540
    "in_payout": Decimal("0.00"),
    "paid_out": Decimal("0.00"),
}


@pytest.fixture
def admin_client(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    return api_client


def _figures(source):
    return {key: Decimal(str(source[key])) for key in FIGURES}


def test_mixed_shop_figures_are_exact_everywhere(admin_client):
    shop = _mixed_shop()

    assert _figures(shop_balance(shop)) == EXPECTED
    annotated = shops_with_balances().get(pk=shop.pk)
    assert _figures(annotated.__dict__) == EXPECTED
    assert annotated.booking_count == 4

    row = admin_client.get("/api/admin/finance/balances").data["results"][0]
    assert _figures(row) == EXPECTED
    detail = admin_client.get(f"/api/admin/shops/{shop.id}").data["balance"]
    assert _figures(detail) == EXPECTED

    summary = admin_client.get("/api/admin/finance/summary").data
    assert _figures(summary) == EXPECTED
    assert summary["order_count"] == 3
    assert summary["line_count"] == 3
    assert summary["booking_count"] == 4

    admin_client.force_authenticate(shop.owner)
    earnings = admin_client.get("/api/vendor/earnings").data
    assert len(earnings) == 1
    assert _figures(earnings[0]) == EXPECTED


def test_cancelled_and_unpaid_bookings_add_nothing():
    shop = _shop()
    for status in (
        Booking.Status.CANCELLED,
        Booking.Status.DECLINED,
        Booking.Status.EXPIRED,
        Booking.Status.REQUESTED,
        Booking.Status.AWAITING_PAYMENT,
    ):
        _booking(shop, status)

    assert all(shop_balance(shop)[key] == Decimal("0.00") for key in FIGURES)
    assert all(platform_summary()[key] == Decimal("0.00") for key in FIGURES)


def test_summary_dates_bookings_by_when_they_were_paid():
    shop = _shop()
    _booking(shop, Booking.Status.COMPLETED)
    tomorrow = timezone.localdate() + timedelta(days=1)

    assert platform_summary()["available_balance"] == Decimal("180.00")
    later = platform_summary(date_from=tomorrow)
    assert later["available_balance"] == Decimal("0.00")
    assert later["booking_count"] == 0


def test_bookings_alone_decide_the_balance_order():
    goods_shop = _shop()
    _line(goods_shop)  # 90 available
    booking_shop = _shop()
    _booking(booking_shop, Booking.Status.COMPLETED)  # 180 available

    order = [shop.pk for shop in shops_with_balances().filter(pk__in=[goods_shop.pk, booking_shop.pk])]

    assert order == [booking_shop.pk, goods_shop.pk]


def test_payout_claims_lines_and_bookings_and_counts_them_once(admin_client):
    shop = _mixed_shop()

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 201
    assert response.data["status"] == "SUCCEEDED"
    assert response.data["amount"] == "720.00"
    payout = Payout.objects.get(pk=response.data["id"])
    assert payout.items.count() == 2
    assert payout.bookings.count() == 3
    assert not payout.bookings.exclude(
        status__in=[Booking.Status.COMPLETED, Booking.Status.NO_SHOW]
    ).exists()

    listed = admin_client.get("/api/admin/payouts").data["results"][0]
    assert listed["line_count"] == 5
    assert listed["booking_count"] == 3

    detail = admin_client.get(f"/api/admin/payouts/{payout.id}").data
    assert len(detail["items"]) == 2
    assert len(detail["bookings"]) == 3
    assert {row["vendor_earning"] for row in detail["bookings"]} == {"180.00"}
    assert detail["bookings"][0]["service_name"]

    figures = shop_balance(shop)
    assert figures["available_balance"] == Decimal("0.00")
    assert figures["paid_out"] == Decimal("720.00")
    assert figures["gross_sales"] == EXPECTED["gross_sales"]


def test_booking_only_shop_can_be_paid_out(admin_client):
    shop = _shop()
    _booking(shop, Booking.Status.NO_SHOW)

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 201
    assert response.data["amount"] == "180.00"


def test_failure_releases_both_and_retry_reclaims_both(admin_client):
    shop = _mixed_shop(phone=disbursement.MOCK_FAILING_PHONE)

    response = admin_client.post(f"/api/admin/shops/{shop.id}/payouts")

    assert response.status_code == 201
    assert response.data["status"] == "FAILED"
    payout_id = response.data["id"]
    assert not OrderItem.objects.filter(payout_id=payout_id).exists()
    assert not Booking.objects.filter(payout_id=payout_id).exists()
    assert shop_balance(shop)["available_balance"] == EXPECTED["available_balance"]
    assert shop_balance(shop)["in_payout"] == Decimal("0.00")

    shop.payout_phone = "+255712345678"
    shop.save()
    response = admin_client.post(f"/api/admin/payouts/{payout_id}/retry")

    assert response.status_code == 200
    assert response.data["status"] == "SUCCEEDED"
    assert response.data["amount"] == "720.00"
    assert OrderItem.objects.filter(payout_id=payout_id).count() == 2
    assert Booking.objects.filter(payout_id=payout_id).count() == 3


def test_booking_payment_in_transactions(admin_client):
    shop = _shop()
    booking = _booking(
        shop,
        Booking.Status.CONFIRMED,
        customer=None,
        guest_name="Neema Guest",
        guest_email="neema@example.com",
    )
    PaymentRecord.objects.create(
        booking=booking,
        method="mobile_money",
        amount=booking.price,
        status=PaymentRecord.Status.SUCCEEDED,
        transaction_reference="bk-ref-1",
    )

    for search in (str(booking.id), "neema@example", "Neema Guest", "bk-ref"):
        rows = admin_client.get(f"/api/admin/transactions?search={search}").data["results"]
        assert len(rows) == 1, search
    row = rows[0]
    assert row["order_id"] is None
    assert row["booking_id"] == booking.id
    assert row["customer"] == {
        "id": None,
        "name": "Neema Guest",
        "email": "neema@example.com",
        "is_guest": True,
    }
    assert row["commission_total"] == "20.00"
    assert row["shop_count"] == 1
