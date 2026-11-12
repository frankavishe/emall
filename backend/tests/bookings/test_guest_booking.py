"""Guest booking: requesting a service without an account, and following the booking by its
private link (the same pattern as guest checkout)."""

import pytest
from django.core import mail
from django.test import override_settings

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.bookings.services import accept_booking
from tests.bookings.helpers import bookable_service, request_body, verified_customer, visit_time
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

GUEST = {"name": "Ama Owusu", "email": "ama@example.com"}


def _request(client, service, starts_at=None, **guest):
    body = request_body(service, starts_at, **(guest or GUEST))
    return client.post("/api/bookings", body, format="json")


def test_a_guest_booking_is_held_and_both_sides_are_emailed(
    api_client, django_capture_on_commit_callbacks
):
    service = bookable_service()

    with django_capture_on_commit_callbacks(execute=True):
        response = _request(api_client, service)

    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.data["id"])
    assert booking.customer is None
    assert booking.is_guest
    assert booking.guest_name == "Ama Owusu"
    assert booking.guest_email == "ama@example.com"
    assert booking.access_token == response.data["access_token"]
    assert booking.status == Booking.Status.REQUESTED

    recipients = sorted(message.to[0] for message in mail.outbox)
    assert recipients == sorted([service.shop.owner.email, "ama@example.com"])
    vendor_email = next(m for m in mail.outbox if m.to == [service.shop.owner.email])
    assert "Ama Owusu" in vendor_email.body
    guest_email = next(m for m in mail.outbox if m.to == ["ama@example.com"])
    assert f"/bookings/track/{booking.access_token}" in guest_email.body


@pytest.mark.parametrize("missing", ["name", "email"])
def test_a_guest_must_give_a_name_and_email(api_client, missing):
    guest = {**GUEST, missing: ""}

    response = _request(api_client, bookable_service(), **guest)

    assert response.status_code == 400
    assert missing in response.data
    assert not Booking.objects.exists()


def test_a_signed_in_customer_gets_no_token(api_client):
    customer = verified_customer()
    api_client.force_authenticate(customer)

    response = _request(api_client, bookable_service())

    assert response.status_code == 201
    assert "access_token" not in response.data
    booking = Booking.objects.get(pk=response.data["id"])
    assert booking.customer == customer
    assert booking.guest_email == ""
    assert booking.access_token is None


def test_a_signed_in_vendor_or_admin_is_not_treated_as_a_guest(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.RIDER, is_email_verified=True))

    assert _request(api_client, bookable_service()).status_code == 403


@override_settings(BOOKING_MAX_ACTIVE_UNPAID=2)
def test_the_unpaid_limit_applies_per_guest_email(api_client):
    service = bookable_service(capacity=5)

    assert _request(api_client, service, visit_time(10)).status_code == 201
    assert _request(api_client, service, visit_time(11)).status_code == 201
    # The same email in a different case is the same guest.
    refused = _request(
        api_client, service, visit_time(12), name="Ama", email="AMA@Example.com"
    )
    other = _request(api_client, service, visit_time(12), name="Kofi", email="kofi@example.com")

    assert refused.status_code == 400
    assert other.status_code == 201


def test_a_guest_follows_the_booking_by_its_link(api_client):
    service = bookable_service()
    token = _request(api_client, service).data["access_token"]
    booking = Booking.objects.get(access_token=token)
    accept_booking(booking_id=booking.id, owner=service.shop.owner)

    response = api_client.get(f"/api/bookings/track/{token}")

    assert response.status_code == 200
    assert response.data["id"] == booking.id
    assert response.data["status"] == Booking.Status.AWAITING_PAYMENT
    assert [event["status"] for event in response.data["history"]] == [
        Booking.Status.REQUESTED,
        Booking.Status.AWAITING_PAYMENT,
    ]


def test_an_unknown_token_is_not_found(api_client):
    assert api_client.get("/api/bookings/track/nope").status_code == 404
    assert api_client.post("/api/bookings/track/nope/cancel").status_code == 404


def test_a_guest_cancels_by_the_link(api_client, django_capture_on_commit_callbacks):
    service = bookable_service()
    token = _request(api_client, service).data["access_token"]
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(f"/api/bookings/track/{token}/cancel")

    assert response.status_code == 200
    assert response.data["status"] == Booking.Status.CANCELLED
    assert [message.to for message in mail.outbox] == [[service.shop.owner.email]]
    assert "Ama Owusu cancelled" in mail.outbox[0].body


def test_providers_and_admins_see_the_guest(api_client):
    service = bookable_service()
    _request(api_client, service)

    api_client.force_authenticate(service.shop.owner)
    vendor_row = api_client.get("/api/vendor/bookings").data["results"][0]
    assert vendor_row["customer_name"] == "Ama Owusu"
    assert vendor_row["is_guest"] is True

    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    admin = api_client.get("/api/admin/bookings", {"search": "ama@example"}).data["results"]
    assert admin[0]["customer"] == {
        "id": None,
        "name": "Ama Owusu",
        "email": "ama@example.com",
        "is_guest": True,
    }
