import pytest

from apps.accounts.models import User
from tests.factories import (
    OrderFactory,
    OrderItemFactory,
    RiderFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def _login(api_client, email, password=PASSWORD):
    return api_client.post("/api/auth/login", {"email": email, "password": password}, format="json")


def _authenticate(api_client, user, password=PASSWORD):
    response = _login(api_client, user.email, password)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


@pytest.fixture
def admin(api_client):
    user = UserFactory(role=User.Role.ADMINISTRATOR, is_email_verified=True)
    _authenticate(api_client, user)
    return user


def test_list_includes_customers_and_vendors_only(api_client, admin):
    customer = UserFactory(name="Ama Owusu")
    vendor = UserFactory(name="Kofi Shop", is_vendor=True)
    rider = RiderFactory()

    response = api_client.get("/api/admin/customers")

    assert response.status_code == 200
    ids = {row["id"] for row in response.data["results"]}
    assert ids == {customer.id, vendor.id}
    assert rider.id not in ids and admin.id not in ids


def test_list_reports_order_totals_and_shop_count(api_client, admin):
    customer = UserFactory()
    order = OrderFactory(customer=customer)
    OrderItemFactory(order=order, quantity=2, unit_price="10.00")
    OrderItemFactory(order=order, quantity=1, unit_price="5.50")
    OrderItemFactory(order=OrderFactory(customer=customer), quantity=1, unit_price="4.50")
    ShopFactory(owner=customer)
    ShopFactory(owner=customer)

    rows = api_client.get("/api/admin/customers").data["results"]
    row = next(r for r in rows if r["id"] == customer.id)

    assert row["order_count"] == 2
    assert row["total_spent"] == "30.00"
    assert row["shop_count"] == 2


def test_search_and_active_filter(api_client, admin):
    ama = UserFactory(name="Ama Owusu", email="ama@example.com")
    UserFactory(name="Kwame Mensah", email="kwame@example.com")
    blocked = UserFactory(name="Blocked Person", is_active=False)

    by_name = api_client.get("/api/admin/customers", {"q": "owusu"}).data["results"]
    assert [r["id"] for r in by_name] == [ama.id]
    by_email = api_client.get("/api/admin/customers", {"q": "AMA@"}).data["results"]
    assert [r["id"] for r in by_email] == [ama.id]

    inactive = api_client.get("/api/admin/customers", {"is_active": "false"}).data["results"]
    assert [r["id"] for r in inactive] == [blocked.id]
    active = api_client.get("/api/admin/customers", {"is_active": "true"}).data["results"]
    assert blocked.id not in {r["id"] for r in active}


def test_detail_includes_recent_orders(api_client, admin):
    customer = UserFactory()
    order = OrderFactory(customer=customer)
    OrderItemFactory(order=order, quantity=3, unit_price="2.00")

    response = api_client.get(f"/api/admin/customers/{customer.id}")

    assert response.status_code == 200
    assert response.data["email"] == customer.email
    assert response.data["recent_orders"] == [
        {"id": order.id, "placed_at": order.placed_at, "item_count": 1, "total": "6.00"}
    ]


def test_non_admins_are_forbidden(api_client):
    customer = UserFactory()
    _authenticate(api_client, customer)

    assert api_client.get("/api/admin/customers").status_code == 403
    assert api_client.get(f"/api/admin/customers/{customer.id}").status_code == 403
    response = api_client.patch(
        f"/api/admin/customers/{customer.id}", {"is_active": False}, format="json"
    )
    assert response.status_code == 403
    customer.refresh_from_db()
    assert customer.is_active is True


def test_block_logs_customer_out_and_unblock_restores_login(api_client, admin):
    customer = UserFactory()
    customer_client = type(api_client)()
    login = _login(customer_client, customer.email)
    assert login.status_code == 200
    access = login.data["access"]

    response = api_client.patch(
        f"/api/admin/customers/{customer.id}", {"is_active": False}, format="json"
    )
    assert response.status_code == 200
    assert response.data["is_active"] is False

    # Their refresh token is dead, and their still-unexpired access token is refused.
    assert customer_client.post("/api/auth/refresh").status_code == 401
    customer_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert customer_client.get("/api/auth/me").status_code == 401

    # The right password is told the account is blocked; a wrong one gets the generic 401.
    blocked_login = _login(type(api_client)(), customer.email)
    assert blocked_login.status_code == 403
    assert "blocked" in blocked_login.data["detail"]
    wrong_password = _login(type(api_client)(), customer.email, "not-the-password")
    assert wrong_password.status_code == 401
    assert wrong_password.data["detail"] == "Invalid email or password."

    response = api_client.patch(
        f"/api/admin/customers/{customer.id}", {"is_active": True}, format="json"
    )
    assert response.data["is_active"] is True
    assert _login(type(api_client)(), customer.email).status_code == 200


def test_cannot_block_riders_or_admins_here(api_client, admin):
    rider = RiderFactory()
    other_admin = UserFactory(role=User.Role.ADMINISTRATOR)

    for user in (rider, other_admin, admin):
        response = api_client.patch(
            f"/api/admin/customers/{user.id}", {"is_active": False}, format="json"
        )
        assert response.status_code == 404
        user.refresh_from_db()
        assert user.is_active is True


def test_is_active_is_required(api_client, admin):
    customer = UserFactory()
    response = api_client.patch(f"/api/admin/customers/{customer.id}", {}, format="json")
    assert response.status_code == 400
