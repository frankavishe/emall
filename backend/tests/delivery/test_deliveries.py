import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orders.models import OrderItem, OrderItemStatusEvent
from apps.vendors.models import Shop
from tests.factories import OrderItemFactory, RiderFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def _client_for(user):
    client = APIClient()
    response = client.post(
        "/api/auth/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def admin_client():
    return _client_for(UserFactory(role=User.Role.ADMINISTRATOR, is_email_verified=True))


def _line(status=OrderItem.Status.PROCESSING, **kwargs):
    return OrderItemFactory(status=status, **kwargs)


# --- Admin assignment ------------------------------------------------------------------------


@pytest.mark.parametrize("status", [OrderItem.Status.PROCESSING, OrderItem.Status.SHIPPED])
def test_admin_assigns_rider_to_processing_or_shipped_line(admin_client, status):
    rider = RiderFactory(name="Juma")
    item = _line(status=status)

    response = admin_client.post(
        f"/api/admin/order-items/{item.id}/rider", {"rider_id": rider.id}, format="json"
    )

    assert response.status_code == 200
    assert response.data["rider"] == {"id": rider.id, "name": "Juma", "phone": "+255700000001"}
    item.refresh_from_db()
    assert item.rider_id == rider.id
    assert item.rider_assigned_at is not None


@pytest.mark.parametrize(
    "status",
    [OrderItem.Status.PENDING, OrderItem.Status.DELIVERED, OrderItem.Status.CANCELLED],
)
def test_admin_cannot_assign_rider_to_unassignable_line(admin_client, status):
    rider = RiderFactory()
    item = _line(status=status)

    response = admin_client.post(
        f"/api/admin/order-items/{item.id}/rider", {"rider_id": rider.id}, format="json"
    )

    assert response.status_code == 400
    item.refresh_from_db()
    assert item.rider_id is None


def test_admin_cannot_assign_inactive_rider_or_non_rider(admin_client):
    item = _line()
    inactive = RiderFactory(is_active=False)
    customer = UserFactory(role=User.Role.CUSTOMER)

    for rider_id in (inactive.id, customer.id):
        response = admin_client.post(
            f"/api/admin/order-items/{item.id}/rider", {"rider_id": rider_id}, format="json"
        )
        assert response.status_code == 400
    item.refresh_from_db()
    assert item.rider_id is None


def test_admin_unassigns_rider(admin_client):
    item = _line(rider=RiderFactory())

    response = admin_client.post(
        f"/api/admin/order-items/{item.id}/rider", {"rider_id": None}, format="json"
    )

    assert response.status_code == 200
    assert response.data["rider"] is None
    item.refresh_from_db()
    assert item.rider_id is None
    assert item.rider_assigned_at is None


def test_non_admin_cannot_assign(api_client):
    rider = RiderFactory()
    item = _line()
    client = _client_for(rider)
    response = client.post(
        f"/api/admin/order-items/{item.id}/rider", {"rider_id": rider.id}, format="json"
    )
    assert response.status_code == 403


# --- Rider deliveries ------------------------------------------------------------------------


def test_rider_lists_only_own_active_deliveries():
    rider = RiderFactory()
    other_rider = RiderFactory()
    mine = _line(rider=rider)
    _line(rider=other_rider)
    done = _line(status=OrderItem.Status.DELIVERED, rider=rider)

    client = _client_for(rider)
    active = client.get("/api/rider/deliveries")
    assert active.status_code == 200
    assert [d["id"] for d in active.data["results"]] == [mine.id]
    delivery = active.data["results"][0]
    assert delivery["pickup"] == {"shop_name": mine.product.shop.name}
    assert delivery["dropoff"]["address_line"] == "12 Ring Road"
    assert delivery["dropoff"]["phone"] == "+233201234567"

    completed = client.get("/api/rider/deliveries?scope=completed")
    assert [d["id"] for d in completed.data["results"]] == [done.id]


def test_non_rider_cannot_list_deliveries():
    customer = UserFactory(role=User.Role.CUSTOMER)
    assert _client_for(customer).get("/api/rider/deliveries").status_code == 403


def test_rider_picks_up_then_delivers():
    rider = RiderFactory()
    item = _line(rider=rider)
    client = _client_for(rider)

    picked_up = client.patch(
        f"/api/rider/deliveries/{item.id}/status", {"status": "SHIPPED"}, format="json"
    )
    assert picked_up.status_code == 200
    assert picked_up.data["status"] == "SHIPPED"

    delivered = client.patch(
        f"/api/rider/deliveries/{item.id}/status", {"status": "DELIVERED"}, format="json"
    )
    assert delivered.status_code == 200
    assert delivered.data["status"] == "DELIVERED"

    statuses = list(
        OrderItemStatusEvent.objects.filter(order_item=item)
        .order_by("changed_at")
        .values_list("status", flat=True)
    )
    assert statuses == ["SHIPPED", "DELIVERED"]


def test_rider_cannot_skip_steps_or_cancel():
    rider = RiderFactory()
    item = _line(rider=rider)
    client = _client_for(rider)

    skip = client.patch(
        f"/api/rider/deliveries/{item.id}/status", {"status": "DELIVERED"}, format="json"
    )
    assert skip.status_code == 400

    cancel = client.patch(
        f"/api/rider/deliveries/{item.id}/status", {"status": "CANCELLED"}, format="json"
    )
    assert cancel.status_code == 400

    item.refresh_from_db()
    assert item.status == OrderItem.Status.PROCESSING


def test_rider_cannot_update_another_riders_delivery():
    rider = RiderFactory()
    item = _line(rider=RiderFactory())

    response = _client_for(rider).patch(
        f"/api/rider/deliveries/{item.id}/status", {"status": "SHIPPED"}, format="json"
    )

    assert response.status_code == 404
    item.refresh_from_db()
    assert item.status == OrderItem.Status.PROCESSING


# --- Rider shown to the other parties --------------------------------------------------------


def test_vendor_and_customer_see_assigned_rider():
    rider = RiderFactory(name="Juma")
    vendor = UserFactory(role=User.Role.VENDOR)
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    item = _line(rider=rider, product__shop=shop, order__customer=customer)
    expected = {"id": rider.id, "name": "Juma", "phone": "+255700000001"}

    vendor_items = _client_for(vendor).get("/api/vendor/order-items").data["results"]
    assert vendor_items[0]["rider"] == expected

    order = _client_for(customer).get(f"/api/orders/{item.order_id}").data
    assert order["items"][0]["rider"] == expected


def test_admin_order_list_shows_rider(admin_client):
    rider = RiderFactory(name="Juma")
    _line(rider=rider)
    _line()

    results = admin_client.get("/api/admin/order-items").data["results"]
    riders = sorted((r["rider"] or {}).get("name", "") for r in results)
    assert riders == ["", "Juma"]
