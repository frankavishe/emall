"""Requesting a time, the provider's answer, and every allowed and refused status change."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.bookings.models import Booking, BookingStatusEvent
from apps.bookings.services import BookingRefused, request_booking
from apps.vendors.models import Shop
from tests.bookings.helpers import (
    bookable_service,
    request_body,
    verified_customer,
    visit_date,
    visit_time,
)
from tests.factories import BookingFactory, ShopClosureFactory, UserFactory

pytestmark = pytest.mark.django_db


def _slot_starts(api_client, service, local_date=None):
    response = api_client.get(
        f"/api/catalog/services/{service.id}/slots?date={(local_date or visit_date()).isoformat()}"
    )
    assert response.status_code == 200
    return [slot["starts_at"] for slot in response.data["slots"]]


def _as(api_client, user):
    api_client.force_authenticate(user)
    return api_client


def _request(api_client, customer, service, starts_at=None, **extra):
    return _as(api_client, customer).post(
        "/api/bookings", request_body(service, starts_at, **extra), format="json"
    )


# --- Requesting ----------------------------------------------------------------


def test_request_holds_the_time_and_freezes_the_money(api_client):
    service = bookable_service(commission_rate=Decimal("15.00"))

    response = _request(api_client, verified_customer(), service, customer_note="First visit")

    assert response.status_code == 201
    assert response.data["status"] == "REQUESTED"
    assert response.data["starts_at"].endswith("+03:00")
    assert response.data["pay_by"] is None
    booking = Booking.objects.get(pk=response.data["id"])
    assert booking.shop == service.shop
    assert booking.ends_at - booking.starts_at == timedelta(minutes=60)
    assert booking.price == service.price
    assert booking.commission_rate == Decimal("15.00")
    assert booking.commission_amount == Decimal("3000.00")
    assert booking.vendor_earning == Decimal("17000.00")
    assert booking.customer_note == "First visit"
    assert [event.status for event in booking.status_events.all()] == ["REQUESTED"]
    assert AuditEvent.objects.filter(action=AuditAction.BOOKING_REQUESTED).exists()


def test_later_price_and_commission_changes_leave_the_booking_alone(api_client):
    service = bookable_service(commission_rate=Decimal("15.00"))
    response = _request(api_client, verified_customer(), service)

    service.price = Decimal("99999.00")
    service.save()
    service.shop.commission_rate = Decimal("50.00")
    service.shop.save()

    booking = Booking.objects.get(pk=response.data["id"])
    assert booking.price == Decimal("20000.00")
    assert booking.commission_rate == Decimal("15.00")


def test_a_held_time_stops_being_offered_along_with_overlapping_times(api_client):
    service = bookable_service(capacity=1, duration=60)
    assert _request(api_client, verified_customer(), service).status_code == 201
    api_client.force_authenticate(None)

    starts = _slot_starts(api_client, service)

    day = visit_date().isoformat()
    # A 10:00 to 11:00 hold blocks 09:30, 10:00 and 10:30, but not 09:00 or 11:00.
    assert f"{day}T09:00:00+03:00" in starts
    assert f"{day}T09:30:00+03:00" not in starts
    assert f"{day}T10:00:00+03:00" not in starts
    assert f"{day}T10:30:00+03:00" not in starts
    assert f"{day}T11:00:00+03:00" in starts


def test_a_booking_on_another_service_blocks_the_time(api_client):
    haircut = bookable_service(capacity=1, duration=60)
    colour = bookable_service(shop=haircut.shop, duration=60)
    assert _request(api_client, verified_customer(), haircut).status_code == 201

    response = _request(api_client, verified_customer(), colour)

    assert response.status_code == 400
    assert "no longer available" in response.data["detail"]


def test_capacity_two_offers_the_time_until_two_customers_hold_it(api_client):
    service = bookable_service(capacity=2)
    time_text = visit_time().isoformat()

    assert _request(api_client, verified_customer(), service).status_code == 201
    api_client.force_authenticate(None)
    assert time_text in _slot_starts(api_client, service)

    assert _request(api_client, verified_customer(), service).status_code == 201
    api_client.force_authenticate(None)
    assert time_text not in _slot_starts(api_client, service)

    assert _request(api_client, verified_customer(), service).status_code == 400


@pytest.mark.parametrize(
    "description, starts_at",
    [
        ("off the 30-minute step", lambda: visit_time(10, 15)),
        ("outside opening hours", lambda: visit_time(20, 0)),
        ("too late to fit before closing", lambda: visit_time(16, 30)),
        ("beyond the booking window", lambda: visit_time(10, 0, days_ahead=61)),
        ("in the past", lambda: visit_time(10, 0, days_ahead=-1)),
    ],
)
def test_a_time_that_isnt_offered_is_refused(api_client, description, starts_at):
    response = _request(api_client, verified_customer(), bookable_service(), starts_at())

    assert response.status_code == 400, description
    assert not Booking.objects.exists()


def test_a_time_inside_the_minimum_notice_is_refused():
    service = bookable_service()
    now = visit_time(10)

    with pytest.raises(BookingRefused, match="no longer available"):
        request_booking(
            customer=verified_customer(),
            service_id=service.id,
            starts_at=visit_time(12),
            contact_phone="+255712345678",
            now=now,
        )


def test_a_closed_date_is_refused(api_client):
    service = bookable_service()
    ShopClosureFactory(shop=service.shop, date=visit_date())

    assert _request(api_client, verified_customer(), service).status_code == 400


def test_the_response_deadline_shortens_for_a_visit_that_is_soon():
    booking = request_booking(
        customer=verified_customer(),
        service_id=bookable_service().id,
        starts_at=visit_time(12),
        contact_phone="+255712345678",
        now=visit_time(8),
    )

    assert booking.respond_by == visit_time(10, 30)


def test_the_response_deadline_is_twelve_hours_when_the_visit_is_far_off(api_client):
    before = timezone.now()

    response = _request(api_client, verified_customer(), bookable_service())

    booking = Booking.objects.get(pk=response.data["id"])
    assert (
        before + timedelta(hours=12)
        <= booking.respond_by
        <= timezone.now() + timedelta(hours=12)
    )


def test_a_bad_phone_is_refused(api_client):
    response = _request(
        api_client, verified_customer(), bookable_service(), contact_phone="not a phone"
    )

    assert response.status_code == 400
    assert "contact_phone" in response.data


def test_an_unpublished_service_cant_be_booked(api_client):
    service = bookable_service()
    service.is_published = False
    service.save()

    assert _request(api_client, verified_customer(), service).status_code == 404


def test_an_unapproved_shops_service_cant_be_booked(api_client):
    service = bookable_service()
    Shop.objects.filter(pk=service.shop_id).update(status=Shop.Status.PENDING)

    assert _request(api_client, verified_customer(), service).status_code == 404


def test_the_provider_is_emailed_about_a_new_request(
    api_client, django_capture_on_commit_callbacks
):
    service = bookable_service()

    with django_capture_on_commit_callbacks(execute=True):
        _request(api_client, verified_customer(), service)

    assert [message.to for message in mail.outbox] == [[service.shop.owner.email]]


def test_a_failed_email_doesnt_stop_the_booking(
    api_client, django_capture_on_commit_callbacks, monkeypatch
):
    def explode(*args, **kwargs):
        raise RuntimeError("SMTP is down")

    monkeypatch.setattr("apps.core.email.send_mail", explode)

    with django_capture_on_commit_callbacks(execute=True):
        response = _request(api_client, verified_customer(), bookable_service())

    assert response.status_code == 201


# --- The provider's answer -----------------------------------------------------


def _vendor_post(api_client, booking, action, body=None):
    return _as(api_client, booking.shop.owner).post(
        f"/api/vendor/bookings/{booking.id}/{action}", body or {}, format="json"
    )


def test_accept_moves_to_awaiting_payment_and_sets_the_deadline(
    api_client, django_capture_on_commit_callbacks
):
    booking = BookingFactory()
    before = timezone.now()

    with django_capture_on_commit_callbacks(execute=True):
        response = _vendor_post(api_client, booking, "accept")

    assert response.status_code == 200
    assert response.data["status"] == "AWAITING_PAYMENT"
    booking.refresh_from_db()
    assert booking.accepted_at is not None
    assert (
        before + timedelta(hours=6) <= booking.pay_by <= timezone.now() + timedelta(hours=6)
    )
    assert mail.outbox[-1].to == [booking.customer.email]
    assert AuditEvent.objects.filter(action=AuditAction.BOOKING_ACCEPTED).exists()


def test_accept_shortens_the_payment_deadline_for_a_visit_that_is_soon(api_client):
    starts_at = timezone.now() + timedelta(hours=3)
    booking = BookingFactory(starts_at=starts_at)

    _vendor_post(api_client, booking, "accept")

    booking.refresh_from_db()
    assert booking.pay_by == starts_at - timedelta(minutes=60)


def test_decline_ends_the_booking_and_frees_the_time(
    api_client, django_capture_on_commit_callbacks
):
    service = bookable_service()
    customer = verified_customer()
    booking = Booking.objects.get(pk=_request(api_client, customer, service).data["id"])
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        response = _vendor_post(api_client, booking, "decline", {"reason": "Fully booked"})

    assert response.status_code == 200
    assert response.data["status"] == "DECLINED"
    assert response.data["status_reason"] == "Fully booked"
    assert mail.outbox[-1].to == [customer.email]
    api_client.force_authenticate(None)
    assert visit_time().isoformat() in _slot_starts(api_client, service)
    assert list(
        BookingStatusEvent.objects.filter(booking=booking).values_list("status", flat=True)
    ) == ["REQUESTED", "DECLINED"]


def test_decline_works_without_a_reason(api_client):
    assert _vendor_post(api_client, BookingFactory(), "decline").status_code == 200


@pytest.mark.parametrize("action", ["accept", "decline"])
@pytest.mark.parametrize(
    "status",
    [
        Booking.Status.AWAITING_PAYMENT,
        Booking.Status.CONFIRMED,
        Booking.Status.COMPLETED,
        Booking.Status.NO_SHOW,
        Booking.Status.DECLINED,
        Booking.Status.EXPIRED,
        Booking.Status.CANCELLED,
    ],
)
def test_only_a_request_can_be_answered(api_client, status, action):
    booking = BookingFactory(status=status, pay_by=timezone.now() + timedelta(hours=1))

    response = _vendor_post(api_client, booking, action)

    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == status


def test_a_late_accept_is_refused_and_the_booking_expires(api_client):
    booking = BookingFactory(respond_by=timezone.now() - timedelta(minutes=1))

    response = _vendor_post(api_client, booking, "accept")

    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == Booking.Status.EXPIRED


@pytest.mark.parametrize("action", ["accept", "decline"])
def test_an_unapproved_shop_cant_answer(api_client, action):
    booking = BookingFactory()
    Shop.objects.filter(pk=booking.shop_id).update(status=Shop.Status.REJECTED)

    response = _vendor_post(api_client, booking, action)

    assert response.status_code == 403
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REQUESTED


# --- Customer cancellation -----------------------------------------------------


def _customer_cancel(api_client, booking):
    return _as(api_client, booking.customer).post(
        f"/api/bookings/{booking.id}/cancel", {}, format="json"
    )


def test_customer_cancels_a_request(api_client, django_capture_on_commit_callbacks):
    booking = BookingFactory()

    with django_capture_on_commit_callbacks(execute=True):
        response = _customer_cancel(api_client, booking)

    assert response.status_code == 200
    assert response.data["status"] == "CANCELLED"
    booking.refresh_from_db()
    assert booking.cancelled_at is not None
    assert mail.outbox[-1].to == [booking.shop.owner.email]
    assert AuditEvent.objects.filter(action=AuditAction.BOOKING_CANCELLED).exists()


def test_customer_cancels_an_accepted_unpaid_booking(api_client):
    booking = BookingFactory(
        status=Booking.Status.AWAITING_PAYMENT, pay_by=timezone.now() + timedelta(hours=1)
    )

    assert _customer_cancel(api_client, booking).status_code == 200


# CONFIRMED is cancellable 24+ hours ahead (FR-024); see tests/bookings/test_refunds.py.
@pytest.mark.parametrize(
    "status",
    [
        Booking.Status.COMPLETED,
        Booking.Status.NO_SHOW,
        Booking.Status.DECLINED,
        Booking.Status.EXPIRED,
        Booking.Status.CANCELLED,
    ],
)
def test_customer_cant_cancel_in_other_statuses(api_client, status):
    booking = BookingFactory(status=status)

    assert _customer_cancel(api_client, booking).status_code == 409


# --- Closures ------------------------------------------------------------------


def test_closing_a_day_warns_about_its_bookings_and_leaves_them_alone(api_client):
    service = bookable_service()
    held = BookingFactory(service=service, starts_at=visit_time(10))
    BookingFactory(service=service, starts_at=visit_time(11), status=Booking.Status.DECLINED)
    BookingFactory(service=service, starts_at=visit_time(10, days_ahead=8))

    response = _as(api_client, service.shop.owner).post(
        f"/api/vendor/shops/{service.shop_id}/closures",
        {"date": visit_date().isoformat()},
        format="json",
    )

    assert response.status_code == 201
    assert [row["id"] for row in response.data["active_bookings"]] == [held.id]
    assert response.data["active_bookings"][0]["customer_name"] == held.customer.name
    held.refresh_from_db()
    assert held.status == Booking.Status.REQUESTED


# --- Reading -------------------------------------------------------------------


def test_customer_sees_status_deadlines_and_history(api_client):
    booking = BookingFactory()
    _vendor_post(api_client, booking, "accept")

    response = _as(api_client, booking.customer).get(f"/api/bookings/{booking.id}")

    assert response.status_code == 200
    assert response.data["status"] == "AWAITING_PAYMENT"
    assert response.data["pay_by"].endswith("+03:00")
    assert response.data["service"]["name"] == booking.service.name
    assert response.data["shop"]["name"] == booking.shop.name
    assert [event["status"] for event in response.data["history"]] == ["AWAITING_PAYMENT"]


def test_lists_filter_by_status(api_client):
    customer = verified_customer()
    waiting = BookingFactory(customer=customer)
    BookingFactory(customer=customer, status=Booking.Status.DECLINED)

    response = _as(api_client, customer).get("/api/bookings?status=REQUESTED")

    assert [row["id"] for row in response.data["results"]] == [waiting.id]


def test_vendor_list_filters_by_shop_and_shows_the_customer(api_client):
    owner = UserFactory(role=User.Role.VENDOR)
    first = bookable_service(owner=owner)
    second = bookable_service(owner=owner)
    wanted = BookingFactory(service=first)
    BookingFactory(service=second)

    response = _as(api_client, owner).get(f"/api/vendor/bookings?shop={first.shop_id}")

    assert [row["id"] for row in response.data["results"]] == [wanted.id]
    assert response.data["results"][0]["customer_name"] == wanted.customer.name
    assert response.data["results"][0]["contact_phone"] == wanted.contact_phone
    assert response.data["results"][0]["vendor_earning"] == "18000.00"
