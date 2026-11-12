"""T084: booking and service lists run a fixed number of queries however many rows they show."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import User
from apps.core.admin_permissions import AdminRole
from tests.factories import BookingFactory, ServiceFactory, ServicesShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _query_count(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200, response.data
    return len(queries)


def _assert_flat(client, url, add_row):
    add_row()
    one = _query_count(client, url)
    for _ in range(4):
        add_row()
    assert _query_count(client, url) == one


def test_public_service_list(api_client):
    _assert_flat(api_client, "/api/catalog/services", ServiceFactory)


def test_vendor_service_list(api_client):
    shop = ServicesShopFactory()
    api_client.force_authenticate(shop.owner)
    _assert_flat(api_client, "/api/vendor/services", lambda: ServiceFactory(shop=shop))


def test_customer_booking_list(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER, is_email_verified=True)
    api_client.force_authenticate(customer)
    _assert_flat(api_client, "/api/bookings", lambda: BookingFactory(customer=customer))


def test_vendor_booking_list(api_client):
    service = ServiceFactory()
    api_client.force_authenticate(service.shop.owner)
    _assert_flat(api_client, "/api/vendor/bookings", lambda: BookingFactory(service=service))


def test_admin_booking_list(api_client):
    api_client.force_authenticate(
        UserFactory(role=User.Role.ADMINISTRATOR, admin_role=AdminRole.SUPPORT_ADMIN)
    )

    def add_row():
        BookingFactory()
        BookingFactory(customer=None, guest_name="Ama", guest_email="ama@example.com")

    _assert_flat(api_client, "/api/admin/bookings", add_row)
