"""Shared setup for booking payment tests: accepted bookings, the AzamPay simulator, and callbacks
shaped exactly like the ones AzamPay sends."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.payments.models import PaymentRecord
from apps.payments.services import azampay_amount
from tests.factories import BookingFactory, UserFactory

CALLBACK_TOKEN = "test-callback-token"


@pytest.fixture(autouse=True)
def simulator_backend(settings):
    settings.PAYMENT_BACKEND = "azampay_simulator"
    settings.AZAMPAY_CALLBACK_TOKEN = CALLBACK_TOKEN
    settings.PAYMENT_PENDING_TIMEOUT_MINUTES = 15


def accepted_booking(*, starts_in=timedelta(days=7), pay_within=timedelta(hours=6), **fields):
    now = timezone.now()
    return BookingFactory(
        status=Booking.Status.AWAITING_PAYMENT,
        starts_at=now + starts_in,
        accepted_at=now,
        pay_by=now + min(pay_within, starts_in - timedelta(minutes=60)),
        **fields,
    )


def confirmed_booking(*, starts_in=timedelta(days=7), method="mobile_money", **fields):
    booking = accepted_booking(starts_in=starts_in, **fields)
    booking.status = Booking.Status.CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.save(update_fields=["status", "confirmed_at"])
    PaymentRecord.objects.create(
        booking=booking,
        method=method,
        amount=booking.amount_due(),
        status=PaymentRecord.Status.SUCCEEDED,
        transaction_reference=f"paid-{booking.id}",
    )
    return booking


def as_user(client, user):
    client.force_authenticate(user)
    return client


def finance_admin():
    return UserFactory(role=User.Role.ADMINISTRATOR, admin_role="SUPER_ADMIN")


def support_admin():
    return UserFactory(role=User.Role.ADMINISTRATOR, admin_role="SUPPORT_ADMIN")


def pay(client, booking, **body):
    body = body or {"payment_method": "mobile_money", "provider": "Mpesa", "msisdn": "0712345678"}
    return client.post(f"/api/bookings/{booking.id}/pay", body, format="json")


def callback(client, record, *, success=True, amount=None):
    client.force_authenticate(None)
    return client.post(
        f"/api/payments/azampay/callback/{CALLBACK_TOKEN}",
        {
            "msisdn": record.msisdn,
            "amount": amount if amount is not None else azampay_amount(record.amount),
            "message": "Payment successful" if success else "Customer rejected the payment",
            "utilityref": record.transaction_reference,
            "operator": record.provider,
            "reference": f"MNO-{record.id}",
            "transactionstatus": "success" if success else "failure",
        },
        format="json",
    )
