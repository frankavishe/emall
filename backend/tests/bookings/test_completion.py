"""US4: a provider marks a confirmed visit completed or a no-show once it has started, and the
earning, fixed when the booking was requested, becomes available for payout (FR-028)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.bookings.models import Booking, BookingStatusEvent
from apps.finance.models import PlatformSettings
from apps.finance.services import shop_balance
from apps.payments.models import PaymentRecord
from tests.bookings.payment_helpers import as_user
from tests.factories import BookingFactory, ServiceFactory, UserFactory

pytestmark = pytest.mark.django_db

ACTIONS = {
    "complete": (Booking.Status.COMPLETED, AuditAction.BOOKING_COMPLETED),
    "no-show": (Booking.Status.NO_SHOW, AuditAction.BOOKING_NO_SHOW),
}


def _confirmed(*, started=timedelta(minutes=10), **fields):
    """A paid booking whose visit started `started` ago (negative: still to come)."""

    now = timezone.now()
    fields.setdefault("service", ServiceFactory(price=Decimal("200.00")))
    booking = BookingFactory(
        status=Booking.Status.CONFIRMED,
        starts_at=now - started,
        respond_by=now - started - timedelta(days=2),
        accepted_at=now - started - timedelta(days=2),
        confirmed_at=now - started - timedelta(days=1),
        **fields,
    )
    PaymentRecord.objects.create(
        booking=booking,
        method="mobile_money",
        amount=booking.amount_due(),
        status=PaymentRecord.Status.SUCCEEDED,
        transaction_reference=f"paid-{booking.id}",
    )
    return booking


def _post(client, booking, action, user=None):
    as_user(client, user or booking.shop.owner)
    return client.post(f"/api/vendor/bookings/{booking.id}/{action}")


@pytest.mark.parametrize("action", ACTIONS)
def test_refused_before_the_visit_starts(api_client, action):
    booking = _confirmed(started=-timedelta(minutes=5))

    response = _post(api_client, booking, action)

    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.completed_at is None


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize(
    "status",
    [
        Booking.Status.REQUESTED,
        Booking.Status.AWAITING_PAYMENT,
        Booking.Status.CANCELLED,
        Booking.Status.COMPLETED,
        Booking.Status.NO_SHOW,
    ],
)
def test_only_a_confirmed_booking_can_be_finished(api_client, action, status):
    booking = _confirmed()
    Booking.objects.filter(pk=booking.pk).update(status=status)

    response = _post(api_client, booking, action)

    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == status


@pytest.mark.parametrize("action", ACTIONS)
def test_another_providers_booking_is_not_found(api_client, action):
    booking = _confirmed()
    stranger = UserFactory(role="VENDOR")

    response = _post(api_client, booking, action, user=stranger)

    assert response.status_code == 404
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


@pytest.mark.parametrize("action", ACTIONS)
def test_completed_and_no_show_both_earn(api_client, action):
    status, audit_action = ACTIONS[action]
    booking = _confirmed()
    assert shop_balance(booking.shop)["available_balance"] == Decimal("0.00")
    assert shop_balance(booking.shop)["pending_earnings"] == Decimal("180.00")

    response = _post(api_client, booking, action)

    assert response.status_code == 200
    assert response.data["status"] == status
    booking.refresh_from_db()
    assert booking.status == status
    assert booking.completed_at is not None
    assert BookingStatusEvent.objects.filter(
        booking=booking, status=status, actor=booking.shop.owner
    ).exists()
    assert AuditEvent.objects.filter(action=audit_action, target_id=str(booking.id)).exists()

    figures = shop_balance(booking.shop)
    assert figures["available_balance"] == Decimal("180.00")
    assert figures["pending_earnings"] == Decimal("0.00")
    assert figures["commission_earned"] == Decimal("20.00")
    assert figures["gross_sales"] == Decimal("200.00")


def test_fixed_price_and_commission_survive_later_changes(api_client):
    booking = _confirmed()
    assert _post(api_client, booking, "complete").status_code == 200

    booking.service.price = Decimal("999.00")
    booking.service.save()
    booking.shop.commission_rate = Decimal("50.00")
    booking.shop.save()
    platform = PlatformSettings.get_solo()
    platform.default_commission_rate = Decimal("40.00")
    platform.save()

    booking.refresh_from_db()
    assert booking.price == Decimal("200.00")
    assert booking.commission_amount == Decimal("20.00")
    assert booking.vendor_earning == Decimal("180.00")
    assert shop_balance(booking.shop)["available_balance"] == Decimal("180.00")
