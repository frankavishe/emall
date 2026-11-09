"""The Order Oversight badge count and the order details on each oversight row."""

import pytest

from apps.accounts.models import User
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
from tests.factories import OrderFactory, OrderItemFactory, UserFactory

pytestmark = pytest.mark.django_db

SUMMARY_URL = "/api/admin/order-items/summary"


def _admin_client(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    return api_client


def test_counts_paid_orders_with_a_pending_line_once_each(api_client):
    # Needs action: two pending lines on one order still count as one order.
    two_pending = OrderFactory()
    OrderItemFactory(order=two_pending, status=OrderItem.Status.PENDING)
    OrderItemFactory(order=two_pending, status=OrderItem.Status.PENDING)
    # Needs action: one line started, one still pending.
    mixed = OrderFactory()
    OrderItemFactory(order=mixed, status=OrderItem.Status.PROCESSING)
    OrderItemFactory(order=mixed, status=OrderItem.Status.PENDING)
    # Doesn't: every line started or finished.
    OrderItemFactory(order=OrderFactory(), status=OrderItem.Status.PROCESSING)
    OrderItemFactory(order=OrderFactory(), status=OrderItem.Status.CANCELLED)
    # Doesn't: not paid yet, so not in oversight at all.
    unpaid = OrderFactory(status=Order.Status.AWAITING_PAYMENT)
    OrderItemFactory(order=unpaid, status=OrderItem.Status.PENDING)

    response = _admin_client(api_client).get(SUMMARY_URL)

    assert response.status_code == 200
    assert response.data == {"orders_needing_action": 2}


def test_summary_is_admin_only(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.VENDOR))
    assert api_client.get(SUMMARY_URL).status_code == 403


def test_oversight_row_carries_order_details(api_client):
    order = OrderFactory(recipient_name="Ama Owusu", phone="+255700000009", delivery_fee="3.00")
    OrderItemFactory(order=order, status=OrderItem.Status.PENDING, quantity=2, unit_price="5.00")
    OrderItemFactory(order=order, status=OrderItem.Status.PENDING, quantity=1, unit_price="1.50")
    PaymentRecord.objects.create(
        order=order,
        method="cod",
        status=PaymentRecord.Status.PENDING,
        amount="14.50",
        transaction_reference="ref-1",
    )

    response = _admin_client(api_client).get("/api/admin/order-items")

    assert response.status_code == 200
    row = response.data["results"][0]
    details = row["order"]
    assert details["customer"] == {
        "id": order.customer_id,
        "name": order.customer.name,
        "email": order.customer.email,
        "is_guest": False,
    }
    assert details["recipient_name"] == "Ama Owusu"
    assert details["phone"] == "+255700000009"
    assert details["address_line"] == "12 Ring Road"
    assert details["payment"] == {"method": "cod", "status": "PENDING"}
    assert details["total"] == "14.50"
    assert details["line_count"] == 2
    assert details["placed_at"]


def test_oversight_row_for_a_guest_order_without_payment(api_client):
    order = OrderFactory(customer=None, guest_email="guest@example.com", recipient_name="Guest")
    OrderItemFactory(order=order, status=OrderItem.Status.PENDING)

    row = _admin_client(api_client).get("/api/admin/order-items").data["results"][0]

    assert row["order"]["customer"] == {
        "id": None,
        "name": "Guest",
        "email": "guest@example.com",
        "is_guest": True,
    }
    assert row["order"]["payment"] is None
