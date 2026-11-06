"""Real threads against real Postgres: the guarantee that a time can't be double booked."""

import threading

import pytest
from django.db import connections
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from tests.bookings.helpers import (
    bookable_service,
    request_body,
    verified_customer,
    visit_time,
)
from tests.factories import BookingFactory

pytestmark = pytest.mark.django_db(transaction=True)


def _request_at_once(attempts):
    """Sends each `(customer, body)` at the same moment and returns the status codes."""

    results = []
    barrier = threading.Barrier(len(attempts))

    def send(customer, body):
        client = APIClient()
        client.force_authenticate(customer)
        barrier.wait()
        try:
            results.append(client.post("/api/bookings", body, format="json").status_code)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=send, args=attempt) for attempt in attempts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(results)


@pytest.mark.parametrize("run", range(3))
def test_capacity_one_lets_exactly_one_request_through(run):
    service = bookable_service(capacity=1)

    results = _request_at_once([(verified_customer(), request_body(service)) for _ in range(4)])

    assert results == [201, 400, 400, 400]
    assert Booking.objects.filter(shop=service.shop).count() == 1


def test_capacity_two_lets_exactly_two_requests_through():
    service = bookable_service(capacity=2)

    results = _request_at_once([(verified_customer(), request_body(service)) for _ in range(4)])

    assert results == [201, 201, 400, 400]
    assert Booking.objects.filter(shop=service.shop).count() == 2


def test_overlapping_services_share_the_shops_capacity():
    haircut = bookable_service(capacity=1, duration=60)
    colour = bookable_service(shop=haircut.shop, duration=120)

    results = _request_at_once(
        [
            (verified_customer(), request_body(haircut, visit_time(10, 30))),
            (verified_customer(), request_body(colour, visit_time(10, 0))),
        ]
    )

    assert results == [201, 400]
    assert Booking.objects.filter(shop=haircut.shop).count() == 1


def test_one_customer_cant_beat_the_unpaid_limit_across_shops():
    customer = verified_customer()
    for _ in range(2):
        BookingFactory(customer=customer)
    # Two different shops, so only the lock on the customer can serialise these.
    first = bookable_service()
    second = bookable_service()

    results = _request_at_once([(customer, request_body(first)), (customer, request_body(second))])

    assert results == [201, 400]
    assert Booking.objects.filter(customer=customer).count() == 3
