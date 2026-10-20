"""Which sockets hear about each order and payment change (apps.realtime)."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import Order, OrderItem
from apps.orders.services import TransitionError, advance_order_item_status, assign_rider
from apps.payments.models import PaymentRecord
from apps.payments.outcomes import expire_stale_payments, settle_manual_payment
from apps.realtime.groups import ADMINS, order_group, user_group
from apps.vendors.models import Shop
from tests.factories import (
    OrderItemFactory,
    ProductFactory,
    RiderFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Dar es Salaam",
    "region": "Dar es Salaam",
    "postal_code": "11101",
    "country": "Tanzania",
    "phone": "+255712345678",
    "latitude": -6.7924,
    "longitude": 39.2083,
}


@pytest.fixture
def published():
    """Every (groups, event) the code publishes, in order."""

    with mock.patch("apps.realtime.broadcast.publish") as publish:
        yield publish


def _events(published):
    return [(set(call.args[0]), call.args[1]) for call in published.call_args_list]


def _groups_for(published, event_type):
    groups = set()
    for call_groups, event in _events(published):
        if event["type"] == event_type:
            groups |= call_groups
    return groups


@pytest.fixture
def product():
    return ProductFactory(is_published=True, price="5000", stock_quantity=10)


@pytest.fixture
def guest(api_client, product):
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    return api_client


def _checkout(client, method, **extra):
    return client.post(
        "/api/checkout",
        {"shipping": SHIPPING, "payment_method": method, "email": "ama@example.com", **extra},
        format="json",
    )


def test_status_change_reaches_buyer_vendor_rider_and_admins(
    published, django_capture_on_commit_callbacks
):
    rider = RiderFactory()
    item = OrderItemFactory(status=OrderItem.Status.PROCESSING, rider=rider)

    with django_capture_on_commit_callbacks(execute=True):
        advance_order_item_status(order_item=item, new_status=OrderItem.Status.SHIPPED)

    assert _groups_for(published, "order.updated") == {
        order_group(item.order_id),
        user_group(item.order.customer_id),
        ADMINS,
        user_group(item.product.shop.owner_id),
        user_group(rider.id),
    }


def test_rejected_transition_publishes_nothing(published, django_capture_on_commit_callbacks):
    item = OrderItemFactory(status=OrderItem.Status.DELIVERED)

    with django_capture_on_commit_callbacks(execute=True), pytest.raises(TransitionError):
        advance_order_item_status(order_item=item, new_status=OrderItem.Status.PROCESSING)

    published.assert_not_called()


def test_assigning_a_rider_tells_old_and_new_rider(published, django_capture_on_commit_callbacks):
    old, new = RiderFactory(), RiderFactory()
    item = OrderItemFactory(status=OrderItem.Status.PROCESSING, rider=old)

    with django_capture_on_commit_callbacks(execute=True):
        assign_rider(order_item=item, rider=new)

    assert _groups_for(published, "delivery.assigned") == {user_group(old.id), user_group(new.id)}
    assert _groups_for(published, "order.updated") == {
        order_group(item.order_id),
        user_group(item.order.customer_id),
        ADMINS,
        user_group(item.product.shop.owner_id),
    }


def test_cod_order_is_announced_to_its_vendor_and_admins(
    guest, product, published, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        assert _checkout(guest, "cod").status_code == 201

    assert _groups_for(published, "order.created") == {ADMINS, user_group(product.shop.owner_id)}


def test_unpaid_order_reaches_vendor_only_once_paid(
    guest, product, published, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        assert _checkout(guest, "lipa_namba", payer_reference="ABC123").status_code == 202
    order = Order.objects.get()
    assert _groups_for(published, "order.created") == {ADMINS}

    published.reset_mock()
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    with django_capture_on_commit_callbacks(execute=True):
        settle_manual_payment(order=order, admin=admin, confirm=True)

    assert _groups_for(published, "payment.updated") == {order_group(order.id), ADMINS}
    assert _groups_for(published, "order.created") == {user_group(product.shop.owner_id)}


def test_rejected_cod_payment_tells_vendor_lines_were_cancelled(
    guest, product, published, django_capture_on_commit_callbacks
):
    _checkout(guest, "cod")
    order = Order.objects.get()
    admin = UserFactory(role=User.Role.ADMINISTRATOR)

    published.reset_mock()
    with django_capture_on_commit_callbacks(execute=True):
        settle_manual_payment(order=order, admin=admin, confirm=False)

    assert _groups_for(published, "payment.updated") == {order_group(order.id), ADMINS}
    assert _groups_for(published, "order.updated") == {user_group(product.shop.owner_id)}


def test_expired_payment_is_announced(guest, published, django_capture_on_commit_callbacks):
    _checkout(guest, "lipa_namba", payer_reference="ABC123")
    order = Order.objects.get()
    PaymentRecord.objects.update(created_at=timezone.now() - timedelta(days=30))

    published.reset_mock()
    with django_capture_on_commit_callbacks(execute=True):
        assert expire_stale_payments() == 1

    assert _groups_for(published, "payment.updated") == {order_group(order.id), ADMINS}
    # The vendor never saw this unpaid order, so there's nothing to tell them.
    assert _groups_for(published, "order.updated") == set()


def test_already_settled_payment_publishes_nothing(
    guest, published, django_capture_on_commit_callbacks
):
    _checkout(guest, "lipa_namba", payer_reference="ABC123")
    order = Order.objects.get()
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    settle_manual_payment(order=order, admin=admin, confirm=True)

    published.reset_mock()
    with django_capture_on_commit_callbacks(execute=True):
        expire_stale_payments()

    published.assert_not_called()


def _as_admin(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    api_client.force_authenticate(admin)
    return api_client


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_shop_decision_tells_its_owner_and_admins(
    api_client, action, published, django_capture_on_commit_callbacks
):
    owner = UserFactory(role=User.Role.VENDOR, is_email_verified=True)
    shop = ShopFactory(owner=owner, status=Shop.Status.PENDING)

    with django_capture_on_commit_callbacks(execute=True):
        response = _as_admin(api_client).post(f"/api/admin/shops/{shop.id}/{action}")

    assert response.status_code == 200
    assert _events(published) == [
        ({user_group(owner.id), ADMINS}, {"type": "shop.updated", "shop_id": shop.id})
    ]


def test_deciding_a_decided_shop_publishes_nothing(
    api_client, published, django_capture_on_commit_callbacks
):
    shop = ShopFactory(status=Shop.Status.APPROVED)

    with django_capture_on_commit_callbacks(execute=True):
        response = _as_admin(api_client).post(f"/api/admin/shops/{shop.id}/approve")

    assert response.status_code == 409
    assert published.call_count == 0
