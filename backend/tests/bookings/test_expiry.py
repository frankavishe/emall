"""A time frees the moment its deadline passes; the cleanup only updates the status and tells the
customer."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.bookings.models import Booking
from apps.bookings.services import expire_due_bookings
from tests.bookings.helpers import bookable_service, visit_date, visit_time
from tests.factories import BookingFactory

pytestmark = pytest.mark.django_db


def _past():
    return timezone.now() - timedelta(minutes=1)


def _future():
    return timezone.now() + timedelta(hours=1)


def _run_command():
    out = StringIO()
    call_command("expire_bookings", stdout=out)
    return out.getvalue()


def _slot_starts(api_client, service):
    response = api_client.get(
        f"/api/catalog/services/{service.id}/slots?date={visit_date().isoformat()}"
    )
    return [slot["starts_at"] for slot in response.data["slots"]]


def _hold(service, **fields):
    starts_at = visit_time()
    return BookingFactory(
        service=service,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
        **fields,
    )


@pytest.mark.parametrize(
    "fields",
    [
        {"status": Booking.Status.REQUESTED, "respond_by": _past},
        {"status": Booking.Status.AWAITING_PAYMENT, "pay_by": _past},
    ],
)
def test_a_time_frees_before_the_cleanup_runs(api_client, fields):
    service = bookable_service()
    values = {key: value() if callable(value) else value for key, value in fields.items()}
    booking = _hold(service, **values)

    assert visit_time().isoformat() in _slot_starts(api_client, service)
    booking.refresh_from_db()
    assert booking.status == values["status"]


def test_bookings_still_inside_their_deadlines_keep_their_time(api_client):
    service = bookable_service(capacity=3)
    _hold(service, status=Booking.Status.REQUESTED, respond_by=_future())
    _hold(service, status=Booking.Status.AWAITING_PAYMENT, pay_by=_future())
    _hold(service, status=Booking.Status.CONFIRMED)

    assert visit_time().isoformat() not in _slot_starts(api_client, service)


def test_finished_bookings_dont_hold_their_time(api_client):
    service = bookable_service(capacity=1)
    for status in [Booking.Status.DECLINED, Booking.Status.CANCELLED, Booking.Status.EXPIRED]:
        _hold(service, status=status)

    assert visit_time().isoformat() in _slot_starts(api_client, service)


def test_the_command_expires_due_bookings_and_a_second_run_changes_nothing(
    django_capture_on_commit_callbacks,
):
    unanswered = BookingFactory(respond_by=_past())
    unpaid = BookingFactory(status=Booking.Status.AWAITING_PAYMENT, pay_by=_past())
    waiting = BookingFactory()

    with django_capture_on_commit_callbacks(execute=True):
        first = _run_command()
    second = _run_command()

    assert "2" in first
    assert "0" in second
    unanswered.refresh_from_db()
    unpaid.refresh_from_db()
    waiting.refresh_from_db()
    assert unanswered.status == Booking.Status.EXPIRED
    assert unpaid.status == Booking.Status.EXPIRED
    assert waiting.status == Booking.Status.REQUESTED
    assert unanswered.status_events.get().actor is None
    assert sorted(message.to[0] for message in mail.outbox) == sorted(
        [unanswered.customer.email, unpaid.customer.email]
    )
    assert AuditEvent.objects.filter(action=AuditAction.BOOKING_EXPIRED).count() == 2


def test_confirmed_bookings_never_expire():
    booking = BookingFactory(
        status=Booking.Status.CONFIRMED, respond_by=_past(), pay_by=_past()
    )

    assert expire_due_bookings() == 0
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


def test_expiry_can_be_scoped():
    mine = BookingFactory(respond_by=_past())
    theirs = BookingFactory(respond_by=_past())

    assert expire_due_bookings(Booking.objects.filter(customer=mine.customer)) == 1
    theirs.refresh_from_db()
    assert theirs.status == Booking.Status.REQUESTED


def test_reading_a_booking_shows_it_as_expired(api_client):
    booking = BookingFactory(respond_by=_past())
    api_client.force_authenticate(booking.customer)

    response = api_client.get(f"/api/bookings/{booking.id}")

    assert response.data["status"] == "EXPIRED"


def test_an_expired_booking_stops_counting_towards_the_unpaid_limit():
    customer = BookingFactory(respond_by=_past()).customer

    assert Booking.objects.active_unpaid().filter(customer=customer).count() == 0
