"""Money that arrives late: every successful payment must end as a confirmed booking or a refund
entry (SC-004), and repeated callbacks must never create a second one."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import expire_due_bookings
from apps.payments.models import PaymentRecord, RefundDue
from apps.payments.outcomes import EXPIRED_REASON, complete_payment
from tests.bookings.payment_helpers import (
    accepted_booking,
    as_user,
    callback,
    finance_admin,
    pay,
    simulator_backend,  # noqa: F401
)

pytestmark = pytest.mark.django_db


def _pending_push(api_client, booking):
    assert pay(as_user(api_client, booking.customer), booking).status_code == 201
    return PaymentRecord.objects.filter(booking=booking).latest("id")


def _fail(record, message=EXPIRED_REASON):
    complete_payment(record_id=record.id, success=False, message=message)
    record.refresh_from_db()
    return record


def _late_refunds(booking):
    return RefundDue.objects.filter(payment__booking=booking, reason=RefundDue.Reason.LATE_PAYMENT)


def test_late_success_still_confirms_a_booking_that_can_be_honoured(api_client):
    booking = accepted_booking()
    record = _fail(_pending_push(api_client, booking))

    callback(api_client, record, success=True)

    booking.refresh_from_db()
    record.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert record.status == PaymentRecord.Status.SUCCEEDED
    assert not _late_refunds(booking).exists()


def test_late_success_after_the_payment_deadline_is_refunded(api_client):
    booking = accepted_booking()
    record = _fail(_pending_push(api_client, booking))
    Booking.objects.filter(pk=booking.pk).update(pay_by=timezone.now() - timedelta(minutes=1))

    callback(api_client, record, success=True)

    booking.refresh_from_db()
    assert booking.status != Booking.Status.CONFIRMED
    refund = _late_refunds(booking).get()
    assert refund.amount == booking.price
    assert refund.status == RefundDue.Status.DUE


@pytest.mark.parametrize("final_status", ["EXPIRED", "CANCELLED", "DECLINED"])
def test_late_success_on_an_ended_booking_is_refunded(api_client, final_status):
    booking = accepted_booking()
    record = _fail(_pending_push(api_client, booking))
    Booking.objects.filter(pk=booking.pk).update(status=final_status)

    callback(api_client, record, success=True)

    booking.refresh_from_db()
    assert booking.status == final_status
    assert _late_refunds(booking).count() == 1


def test_late_success_when_another_payment_already_succeeded_is_refunded(api_client):
    booking = accepted_booking()
    first = _fail(_pending_push(api_client, booking))
    second = _pending_push(api_client, booking)
    callback(api_client, second, success=True)

    callback(api_client, first, success=True)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert _late_refunds(booking).get().payment_id == first.id
    # Only one live payment per booking, ever.
    assert (
        PaymentRecord.objects.filter(booking=booking, status=PaymentRecord.Status.SUCCEEDED).count()
        == 1
    )


def test_success_after_the_visit_has_started_is_refunded(api_client):
    booking = accepted_booking(starts_in=timedelta(hours=3))
    record = _pending_push(api_client, booking)
    Booking.objects.filter(pk=booking.pk).update(
        starts_at=timezone.now() - timedelta(minutes=1),
        ends_at=timezone.now() + timedelta(minutes=59),
        pay_by=timezone.now() - timedelta(minutes=61),
    )

    callback(api_client, record, success=True)

    booking.refresh_from_db()
    assert booking.status != Booking.Status.CONFIRMED
    assert _late_refunds(booking).count() == 1


def test_lipa_namba_confirmed_after_the_visit_has_started_is_refunded(api_client):
    booking = accepted_booking()
    pay(
        as_user(api_client, booking.customer),
        booking,
        payment_method="lipa_namba",
        payer_reference="ABC123",
    )
    Booking.objects.filter(pk=booking.pk).update(
        starts_at=timezone.now() - timedelta(minutes=1),
        ends_at=timezone.now() + timedelta(minutes=59),
        pay_by=timezone.now() - timedelta(hours=2),
    )
    # The visit time passing ends the booking, but the Lipa record waits for an administrator.
    assert expire_due_bookings() == 1
    booking.refresh_from_db()
    assert booking.status == Booking.Status.EXPIRED
    record = PaymentRecord.objects.get(booking=booking)
    assert record.status == PaymentRecord.Status.PENDING

    response = as_user(api_client, finance_admin()).post(
        f"/api/admin/bookings/{booking.id}/payment/confirm", {}, format="json"
    )

    assert response.status_code == 200
    record.refresh_from_db()
    assert record.status == PaymentRecord.Status.SUCCEEDED
    assert _late_refunds(booking).count() == 1


def test_success_racing_the_sweep_is_refunded_once(api_client, settings):
    booking = accepted_booking()
    record = _pending_push(api_client, booking)
    PaymentRecord.objects.filter(pk=record.pk).update(
        created_at=timezone.now() - timedelta(minutes=settings.PAYMENT_PENDING_TIMEOUT_MINUTES + 1)
    )
    Booking.objects.filter(pk=booking.pk).update(pay_by=timezone.now() - timedelta(minutes=1))

    call_command("expire_bookings")

    record.refresh_from_db()
    booking.refresh_from_db()
    assert record.status == PaymentRecord.Status.FAILED
    assert booking.status == Booking.Status.EXPIRED

    for _ in range(3):
        callback(api_client, record, success=True)

    assert _late_refunds(booking).count() == 1
    booking.refresh_from_db()
    assert booking.status == Booking.Status.EXPIRED


def test_a_late_failure_changes_nothing(api_client):
    booking = accepted_booking()
    record = _fail(_pending_push(api_client, booking))

    callback(api_client, record, success=False)

    assert not RefundDue.objects.exists()
    booking.refresh_from_db()
    assert booking.status == Booking.Status.AWAITING_PAYMENT
