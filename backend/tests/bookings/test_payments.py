"""Paying for an accepted booking: mobile money through the AzamPay simulator, Lipa Namba settled by
an administrator, retries, and the guards that stop a customer being charged twice."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import Booking
from apps.payments.models import PaymentRecord
from tests.bookings.payment_helpers import (
    accepted_booking,
    as_user,
    callback,
    finance_admin,
    pay,
    simulator_backend,  # noqa: F401
    support_admin,
)
from tests.factories import BookingFactory

pytestmark = pytest.mark.django_db

LIPA = {"payment_method": "lipa_namba", "payer_reference": "ABC123XYZ"}


def _record(booking):
    return PaymentRecord.objects.filter(booking=booking).latest("id")


# --- Starting a payment ------------------------------------------------------------------------


def test_payment_is_refused_before_acceptance(api_client):
    booking = BookingFactory()  # REQUESTED

    response = pay(as_user(api_client, booking.customer), booking)

    assert response.status_code == 409
    assert not PaymentRecord.objects.filter(booking=booking).exists()


def test_mobile_money_payment_starts_with_the_server_amount(api_client):
    booking = accepted_booking()

    response = pay(
        as_user(api_client, booking.customer),
        booking,
        payment_method="mobile_money",
        provider="Mpesa",
        msisdn="0712345678",
        amount="1",
    )

    assert response.status_code == 201
    record = _record(booking)
    assert record.status == PaymentRecord.Status.PENDING
    assert record.amount == booking.amount_due()
    assert record.order_id is None
    assert record.msisdn == "255712345678"
    assert record.provider_reference.startswith("SIM")
    assert response.data["payment"]["status"] == "PENDING"


def test_card_and_cash_are_not_offered_for_bookings(api_client):
    booking = accepted_booking()
    client = as_user(api_client, booking.customer)

    methods = {
        row["method"] for row in client.get(f"/api/bookings/{booking.id}/payment-methods").data
    }

    assert methods == {"mobile_money", "lipa_namba"}
    for method in ("card", "cod"):
        assert pay(client, booking, payment_method=method).status_code == 400


def test_a_second_attempt_while_one_is_live_is_refused(api_client):
    booking = accepted_booking()
    client = as_user(api_client, booking.customer)
    assert pay(client, booking).status_code == 201

    response = pay(client, booking)

    assert response.status_code == 409
    assert PaymentRecord.objects.filter(booking=booking).count() == 1


def test_a_rejected_push_fails_the_attempt_but_keeps_the_booking(api_client):
    booking = accepted_booking()

    response = pay(
        as_user(api_client, booking.customer),
        booking,
        payment_method="mobile_money",
        provider="Mpesa",
        msisdn="0712340000",
    )

    assert response.status_code == 400
    assert _record(booking).status == PaymentRecord.Status.FAILED
    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT


def test_someone_else_cannot_pay_or_see_the_booking(api_client):
    booking = accepted_booking()
    stranger = BookingFactory().customer
    client = as_user(api_client, stranger)

    assert pay(client, booking).status_code == 404
    assert client.get(f"/api/bookings/{booking.id}/payment-status").status_code == 404


def test_payment_after_the_deadline_is_refused(api_client):
    booking = accepted_booking()
    Booking.objects.filter(pk=booking.pk).update(pay_by=timezone.now() - timedelta(minutes=1))

    response = pay(as_user(api_client, booking.customer), booking)

    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == Booking.Status.EXPIRED


# --- Callbacks ---------------------------------------------------------------------------------


def test_successful_callback_confirms_the_booking(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking)

    callback(api_client, _record(booking), success=True)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.confirmed_at is not None
    assert _record(booking).status == PaymentRecord.Status.SUCCEEDED
    assert booking.status_events.filter(status="CONFIRMED", actor=None).exists()


def test_failed_callback_keeps_the_booking_and_allows_a_retry(api_client):
    booking = accepted_booking()
    client = as_user(api_client, booking.customer)
    pay(client, booking)
    callback(api_client, _record(booking), success=False)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT
    assert _record(booking).status == PaymentRecord.Status.FAILED

    assert pay(as_user(api_client, booking.customer), booking).status_code == 201
    callback(api_client, _record(booking), success=True)
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert PaymentRecord.objects.filter(booking=booking).count() == 2


def test_a_callback_with_the_wrong_amount_is_ignored(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking)

    callback(api_client, _record(booking), success=True, amount="1")

    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT
    assert _record(booking).status == PaymentRecord.Status.PENDING


def test_a_repeated_callback_changes_nothing(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking)
    record = _record(booking)

    callback(api_client, record, success=True)
    callback(api_client, record, success=True)
    callback(api_client, record, success=False)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.status_events.filter(status="CONFIRMED").count() == 1
    assert _record(booking).status == PaymentRecord.Status.SUCCEEDED


def test_payment_status_reports_the_live_attempt(api_client):
    booking = accepted_booking()
    client = as_user(api_client, booking.customer)
    pay(client, booking)

    data = (
        as_user(api_client, booking.customer).get(f"/api/bookings/{booking.id}/payment-status").data
    )

    assert data["booking_status"] == "AWAITING_PAYMENT"
    assert data["payment_status"] == "PENDING"


def test_a_pending_push_holds_the_time_past_the_payment_deadline(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking)
    Booking.objects.filter(pk=booking.pk).update(pay_by=timezone.now() - timedelta(minutes=1))

    assert Booking.objects.holding().filter(pk=booking.pk).exists()
    callback(api_client, _record(booking), success=True)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


# --- Lipa Namba --------------------------------------------------------------------------------


def test_lipa_namba_is_offered_only_three_hours_or_more_ahead(api_client):
    soon = accepted_booking(starts_in=timedelta(hours=2, minutes=30))
    later = accepted_booking(starts_in=timedelta(hours=4))

    soon_methods = {
        row["method"]
        for row in as_user(api_client, soon.customer)
        .get(f"/api/bookings/{soon.id}/payment-methods")
        .data
    }
    assert "lipa_namba" not in soon_methods
    assert pay(api_client, soon, **LIPA).status_code == 400

    assert pay(as_user(api_client, later.customer), later, **LIPA).status_code == 201
    record = _record(later)
    assert record.method == "lipa_namba"
    assert record.provider_reference == "ABC123XYZ"


def test_lipa_namba_waits_for_an_administrator_and_does_not_time_out(api_client, settings):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking, **LIPA)
    PaymentRecord.objects.filter(booking=booking).update(
        created_at=timezone.now() - timedelta(hours=settings.MANUAL_PAYMENT_TIMEOUT_HOURS + 1)
    )

    from apps.payments.outcomes import expire_stale_payments

    assert expire_stale_payments() == 0
    assert _record(booking).status == PaymentRecord.Status.PENDING


def test_finance_admin_confirms_a_lipa_namba_payment(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking, **LIPA)
    admin = finance_admin()

    response = as_user(api_client, admin).post(
        f"/api/admin/bookings/{booking.id}/payment/confirm", {}, format="json"
    )

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    record = _record(booking)
    assert record.status == PaymentRecord.Status.SUCCEEDED
    assert record.settled_by == admin
    assert (
        api_client.post(
            f"/api/admin/bookings/{booking.id}/payment/confirm", {}, format="json"
        ).status_code
        == 400
    )


def test_finance_admin_rejects_a_lipa_namba_payment(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking, **LIPA)

    response = as_user(api_client, finance_admin()).post(
        f"/api/admin/bookings/{booking.id}/payment/reject",
        {"reason": "Not on the statement"},
        format="json",
    )

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT
    record = _record(booking)
    assert record.status == PaymentRecord.Status.FAILED
    assert record.failure_reason == "Not on the statement"


def test_settling_a_booking_payment_needs_finance_permission(api_client):
    booking = accepted_booking()
    pay(as_user(api_client, booking.customer), booking, **LIPA)

    response = as_user(api_client, support_admin()).post(
        f"/api/admin/bookings/{booking.id}/payment/confirm", {}, format="json"
    )

    assert response.status_code == 403


# --- Guests ------------------------------------------------------------------------------------


def test_a_guest_pays_through_the_tracking_link(api_client):
    booking = accepted_booking(
        customer=None, guest_name="Ama", guest_email="ama@example.com", access_token="tok-123"
    )
    base = "/api/bookings/track/tok-123"

    methods = api_client.get(f"{base}/payment-methods").data
    assert {row["method"] for row in methods} == {"mobile_money", "lipa_namba"}
    response = api_client.post(
        f"{base}/pay",
        {"payment_method": "mobile_money", "provider": "Mpesa", "msisdn": "0712345678"},
        format="json",
    )
    assert response.status_code == 201
    callback(api_client, _record(booking), success=True)

    data = api_client.get(f"{base}/payment-status").data
    assert data["booking_status"] == "CONFIRMED"
    assert data["payment_status"] == "SUCCEEDED"
    assert api_client.post("/api/bookings/track/wrong/pay", {}, format="json").status_code == 404


def test_booking_amount_is_the_frozen_price(api_client):
    booking = accepted_booking(price=Decimal("15000.00"))
    booking.service.price = Decimal("99000.00")
    booking.service.save()

    pay(as_user(api_client, booking.customer), booking)

    assert _record(booking).amount == Decimal("15000.00")
