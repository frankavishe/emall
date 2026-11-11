"""Cancelling after payment, and the refund list administrators pay by hand."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.bookings.models import Booking
from apps.bookings.services import BookingConflict, cancel_customer_booking
from apps.payments.models import PaymentRecord, RefundDue
from tests.bookings.payment_helpers import (
    accepted_booking,
    as_user,
    confirmed_booking,
    finance_admin,
    pay,
    simulator_backend,  # noqa: F401
    support_admin,
)

pytestmark = pytest.mark.django_db


def _cancel(client, booking, who="customer", **body):
    if who == "customer":
        url = f"/api/bookings/{booking.id}/cancel"
    elif who == "provider":
        url = f"/api/vendor/bookings/{booking.id}/cancel"
    else:
        url = f"/api/admin/bookings/{booking.id}/cancel"
    return client.post(url, body, format="json")


# --- Customer --------------------------------------------------------------------------------


def test_customer_cancel_exactly_24_hours_ahead_is_refunded_in_full():
    booking = confirmed_booking()
    now = booking.starts_at - timedelta(hours=24)

    cancel_customer_booking(booking_id=booking.id, customer=booking.customer, now=now)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
    refund = RefundDue.objects.get(payment__booking=booking)
    assert refund.reason == RefundDue.Reason.CUSTOMER_CANCELLED
    assert refund.amount == booking.price
    assert AuditEvent.objects.filter(action=AuditAction.REFUND_CREATED).exists()


def test_customer_cancel_within_24_hours_is_refused_with_a_support_message(api_client):
    booking = confirmed_booking(starts_in=timedelta(hours=23))

    response = _cancel(as_user(api_client, booking.customer), booking)

    assert response.status_code == 409
    assert "support" in response.data["detail"].lower()
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert not RefundDue.objects.exists()


def test_customer_cancel_one_second_inside_24_hours_is_refused():
    booking = confirmed_booking()
    now = booking.starts_at - timedelta(hours=24) + timedelta(seconds=1)

    with pytest.raises(BookingConflict):
        cancel_customer_booking(booking_id=booking.id, customer=booking.customer, now=now)


def test_customer_cancel_before_payment_owes_nothing(api_client):
    booking = accepted_booking()

    response = _cancel(as_user(api_client, booking.customer), booking)

    assert response.status_code == 200
    assert response.data["status"] == "CANCELLED"
    assert not RefundDue.objects.exists()


def test_a_payment_in_progress_blocks_cancelling(api_client):
    booking = accepted_booking()
    client = as_user(api_client, booking.customer)
    pay(client, booking)

    assert _cancel(client, booking).status_code == 409
    assert (
        _cancel(
            as_user(api_client, booking.shop.owner), booking, "provider", reason="Sick"
        ).status_code
        == 409
    )
    admin_response = _cancel(as_user(api_client, finance_admin()), booking, "admin", reason="x")
    assert admin_response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT


def test_guest_cancels_a_paid_booking_through_the_tracking_link(api_client):
    booking = confirmed_booking(
        customer=None, guest_name="Ama", guest_email="ama@example.com", access_token="tok-9"
    )

    response = api_client.post("/api/bookings/track/tok-9/cancel", {}, format="json")

    assert response.status_code == 200
    assert RefundDue.objects.get(payment__booking=booking).reason == "CUSTOMER_CANCELLED"


# --- Provider --------------------------------------------------------------------------------


def test_provider_cancel_needs_a_reason(api_client):
    booking = confirmed_booking()
    client = as_user(api_client, booking.shop.owner)

    assert _cancel(client, booking, "provider").status_code == 400
    assert _cancel(client, booking, "provider", reason="  ").status_code == 400
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


def test_provider_cancel_of_a_paid_booking_refunds_in_full_and_tells_the_customer(
    api_client, django_capture_on_commit_callbacks
):
    booking = confirmed_booking()
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        response = _cancel(
            as_user(api_client, booking.shop.owner), booking, "provider", reason="Chair broken"
        )

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
    assert booking.status_reason == "Chair broken"
    refund = RefundDue.objects.get(payment__booking=booking)
    assert refund.reason == RefundDue.Reason.PROVIDER_CANCELLED
    assert refund.amount == booking.price
    to_customer = [message for message in mail.outbox if booking.customer.email in message.to]
    assert len(to_customer) == 1
    assert "Chair broken" in to_customer[0].body
    assert "refund" in to_customer[0].body


def test_provider_cancel_before_payment_owes_nothing(api_client):
    booking = accepted_booking()

    response = _cancel(
        as_user(api_client, booking.shop.owner), booking, "provider", reason="Closed"
    )

    assert response.status_code == 200
    assert not RefundDue.objects.exists()


def test_another_provider_cannot_cancel(api_client):
    booking = confirmed_booking()
    other = confirmed_booking().shop.owner

    assert _cancel(as_user(api_client, other), booking, "provider", reason="x").status_code == 404


# --- Administrator ---------------------------------------------------------------------------


def test_admin_cancel_refund_defaults_to_the_full_amount(api_client):
    booking = confirmed_booking()

    response = _cancel(as_user(api_client, support_admin()), booking, "admin", reason="Complaint")

    assert response.status_code == 200
    refund = RefundDue.objects.get(payment__booking=booking)
    assert refund.reason == RefundDue.Reason.ADMIN_CANCELLED
    assert refund.amount == booking.price


def test_admin_refund_amount_cannot_exceed_what_was_paid(api_client):
    booking = confirmed_booking(price=Decimal("20000.00"))
    client = as_user(api_client, support_admin())

    assert (
        _cancel(client, booking, "admin", reason="x", refund_amount="20000.01").status_code == 400
    )
    assert _cancel(client, booking, "admin", reason="x", refund_amount="0").status_code == 400
    response = _cancel(client, booking, "admin", reason="x", refund_amount="5000")

    assert response.status_code == 200
    assert RefundDue.objects.get(payment__booking=booking).amount == Decimal("5000.00")


def test_admin_cancel_needs_a_reason_and_bookings_manage(api_client):
    booking = confirmed_booking()

    assert _cancel(as_user(api_client, support_admin()), booking, "admin").status_code == 400
    customer = booking.customer
    assert _cancel(as_user(api_client, customer), booking, "admin", reason="x").status_code == 403


# --- The refund list -------------------------------------------------------------------------


def _due_refund():
    booking = confirmed_booking()
    record = PaymentRecord.objects.get(booking=booking)
    return RefundDue.objects.create(
        payment=record, amount=record.amount, reason=RefundDue.Reason.PROVIDER_CANCELLED
    )


def test_refund_list_shows_the_booking_and_filters_by_status(api_client):
    refund = _due_refund()
    client = as_user(api_client, finance_admin())

    data = client.get("/api/admin/refunds?status=DUE").data

    row = data["results"][0]
    assert row["id"] == refund.id
    assert row["booking_id"] == refund.payment.booking_id
    assert row["amount"] == "20000.00"
    assert row["reason"] == "PROVIDER_CANCELLED"
    assert client.get("/api/admin/refunds?status=PAID").data["results"] == []


def test_mark_paid_needs_finance_manage(api_client):
    refund = _due_refund()

    response = as_user(api_client, support_admin()).post(
        f"/api/admin/refunds/{refund.id}/mark-paid", {"paid_reference": "TX1"}, format="json"
    )

    assert response.status_code == 403
    assert as_user(api_client, support_admin()).get("/api/admin/refunds").status_code == 403


def test_mark_paid_records_who_and_when_and_works_once(api_client):
    refund = _due_refund()
    admin = finance_admin()
    client = as_user(api_client, admin)
    url = f"/api/admin/refunds/{refund.id}/mark-paid"

    assert client.post(url, {}, format="json").status_code == 400
    response = client.post(url, {"paid_reference": "MPESA-TX1"}, format="json")

    assert response.status_code == 200
    refund.refresh_from_db()
    assert refund.status == RefundDue.Status.PAID
    assert refund.paid_reference == "MPESA-TX1"
    assert refund.paid_by == admin
    assert refund.paid_at is not None
    assert AuditEvent.objects.filter(action=AuditAction.REFUND_PAID).exists()

    again = client.post(url, {"paid_reference": "MPESA-TX2"}, format="json")
    assert again.status_code == 409
    refund.refresh_from_db()
    assert refund.paid_reference == "MPESA-TX1"


def test_customer_cancel_in_the_past_is_not_possible():
    booking = confirmed_booking()
    with pytest.raises(BookingConflict):
        cancel_customer_booking(
            booking_id=booking.id, customer=booking.customer, now=timezone.now() + timedelta(days=8)
        )
