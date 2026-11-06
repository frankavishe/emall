"""Who can request, see and answer a booking (FR-011, FR-014, FR-015, FR-035)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.bookings.slots import market_zone
from apps.core.admin_permissions import AdminRole
from tests.bookings.helpers import bookable_service, request_body, verified_customer
from tests.factories import BookingFactory, ServicesShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _admin(admin_role=AdminRole.SUPPORT_ADMIN):
    return UserFactory(role=User.Role.ADMINISTRATOR, admin_role=admin_role)


# --- Requesting ----------------------------------------------------------------


def test_a_guest_cant_request(api_client):
    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 401


def test_an_unverified_customer_is_told_to_verify(api_client):
    api_client.force_authenticate(UserFactory(is_email_verified=False))

    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 403
    assert "verified email" in response.data["detail"]
    assert not Booking.objects.exists()


def test_a_rider_cant_request(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.RIDER, is_email_verified=True))

    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 403


def test_a_vendor_can_book_someone_elses_shop(api_client):
    """A vendor account is also a customer account (one email, both modes)."""

    api_client.force_authenticate(UserFactory(role=User.Role.VENDOR, is_email_verified=True))

    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 201


def test_an_owner_cant_book_their_own_shop(api_client):
    customer = verified_customer()
    shop = ServicesShopFactory(owner=customer)
    api_client.force_authenticate(customer)

    response = api_client.post(
        "/api/bookings", request_body(bookable_service(shop=shop)), format="json"
    )

    assert response.status_code == 403
    assert not Booking.objects.exists()


def test_a_fourth_active_unpaid_booking_is_refused(api_client):
    customer = verified_customer()
    BookingFactory(customer=customer)
    BookingFactory(customer=customer)
    BookingFactory(
        customer=customer,
        status=Booking.Status.AWAITING_PAYMENT,
        pay_by=timezone.now() + timedelta(hours=1),
    )
    api_client.force_authenticate(customer)

    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 400
    assert "3" in response.data["detail"]


@pytest.mark.parametrize(
    "fields",
    [
        {"status": Booking.Status.CONFIRMED},
        {"status": Booking.Status.CANCELLED},
        {"status": Booking.Status.DECLINED},
    ],
)
def test_paid_and_finished_bookings_dont_count_towards_the_limit(api_client, fields):
    customer = verified_customer()
    for _ in range(3):
        BookingFactory(customer=customer, **fields)
    api_client.force_authenticate(customer)

    response = api_client.post("/api/bookings", request_body(bookable_service()), format="json")

    assert response.status_code == 201


def test_booking_requests_are_throttled_but_reading_is_not(api_client, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"booking_request": "1/min"})
    api_client.force_authenticate(verified_customer())
    body = request_body(bookable_service())

    assert api_client.post("/api/bookings", body, format="json").status_code == 201
    assert api_client.post("/api/bookings", body, format="json").status_code == 429
    assert api_client.get("/api/bookings").status_code == 200


# --- Other people's bookings ---------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [("get", ""), ("post", "/cancel")],
)
def test_another_customers_booking_is_not_found(api_client, method, path):
    booking = BookingFactory()
    api_client.force_authenticate(verified_customer())

    response = getattr(api_client, method)(f"/api/bookings/{booking.id}{path}", {}, format="json")

    assert response.status_code == 404
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REQUESTED


def test_a_customers_list_only_has_their_own_bookings(api_client):
    mine = BookingFactory()
    BookingFactory()
    api_client.force_authenticate(mine.customer)

    response = api_client.get("/api/bookings")

    assert [row["id"] for row in response.data["results"]] == [mine.id]


@pytest.mark.parametrize(
    "method, path",
    [("get", ""), ("post", "/accept"), ("post", "/decline")],
)
def test_another_providers_booking_is_not_found(api_client, method, path):
    booking = BookingFactory()
    api_client.force_authenticate(UserFactory(role=User.Role.VENDOR))

    response = getattr(api_client, method)(
        f"/api/vendor/bookings/{booking.id}{path}", {}, format="json"
    )

    assert response.status_code == 404
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REQUESTED


def test_a_providers_list_only_has_their_own_shops(api_client):
    mine = BookingFactory()
    BookingFactory()
    api_client.force_authenticate(mine.shop.owner)

    response = api_client.get("/api/vendor/bookings")

    assert [row["id"] for row in response.data["results"]] == [mine.id]


def test_a_customer_cant_use_the_provider_endpoints(api_client):
    booking = BookingFactory()
    api_client.force_authenticate(booking.customer)

    assert api_client.post(f"/api/vendor/bookings/{booking.id}/accept").status_code == 403


# --- Administrators ------------------------------------------------------------


@pytest.mark.parametrize("admin_role", [AdminRole.SUPER_ADMIN, AdminRole.SUPPORT_ADMIN])
def test_admin_tiers_can_view_bookings(api_client, admin_role):
    booking = BookingFactory()
    api_client.force_authenticate(_admin(admin_role))

    listing = api_client.get("/api/admin/bookings")
    detail = api_client.get(f"/api/admin/bookings/{booking.id}")

    assert [row["id"] for row in listing.data["results"]] == [booking.id]
    assert detail.status_code == 200
    assert detail.data["customer"]["email"] == booking.customer.email
    assert detail.data["history"] == []


def test_an_admin_with_no_tier_cant_view_bookings(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR, admin_role=None))

    assert api_client.get("/api/admin/bookings").status_code == 403


@pytest.mark.parametrize("role", [User.Role.CUSTOMER, User.Role.VENDOR])
def test_non_admins_cant_view_all_bookings(api_client, role):
    api_client.force_authenticate(UserFactory(role=role))

    assert api_client.get("/api/admin/bookings").status_code == 403


def test_admin_list_filters(api_client):
    wanted = BookingFactory()
    other = BookingFactory(status=Booking.Status.DECLINED)
    api_client.force_authenticate(_admin())

    by_status = api_client.get("/api/admin/bookings?status=REQUESTED")
    by_shop = api_client.get(f"/api/admin/bookings?shop={other.shop_id}")
    by_search = api_client.get(f"/api/admin/bookings?search={wanted.customer.email}")
    day = wanted.starts_at.astimezone(market_zone()).date().isoformat()
    by_date = api_client.get(f"/api/admin/bookings?date_from={day}&date_to={day}")
    bad_date = api_client.get("/api/admin/bookings?date_from=soon")

    assert [row["id"] for row in by_status.data["results"]] == [wanted.id]
    assert [row["id"] for row in by_shop.data["results"]] == [other.id]
    assert [row["id"] for row in by_search.data["results"]] == [wanted.id]
    assert {row["id"] for row in by_date.data["results"]} == {wanted.id, other.id}
    assert bad_date.status_code == 400
