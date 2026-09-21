import pytest

from apps.accounts.models import User
from apps.orders.models import OrderItem
from apps.orders.services import advance_order_item_status
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Accra",
    "region": "Greater Accra",
    "postal_code": "GA-184-9021",
    "country": "Ghana",
    "phone": "+233201234567",
}


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _place_order_line(api_client, customer, vendor, shop_name="Kofi's Electronics", quantity=2):
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED, name=shop_name)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
    )
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    return product, shop


def test_admin_order_item_list_spans_every_shop_with_history(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)
    admin = UserFactory(role=User.Role.ADMINISTRATOR)

    product_a, shop_a = _place_order_line(api_client, customer, vendor_a, "Shop A")
    product_b, shop_b = _place_order_line(api_client, customer, vendor_b, "Shop B")

    item_a = OrderItem.objects.get(product=product_a)
    advance_order_item_status(order_item=item_a, new_status=OrderItem.Status.PROCESSING)
    item_a.refresh_from_db()
    advance_order_item_status(order_item=item_a, new_status=OrderItem.Status.SHIPPED)

    _authenticate(api_client, admin)
    response = api_client.get("/api/admin/order-items")

    assert response.status_code == 200
    rows = {row["id"]: row for row in response.data["results"]}
    assert set(rows) == {item_a.id, OrderItem.objects.get(product=product_b).id}

    row_a = rows[item_a.id]
    assert row_a["shop"] == {"id": shop_a.id, "name": "Shop A"}
    assert row_a["status"] == "SHIPPED"
    assert [event["status"] for event in row_a["status_history"]] == [
        "PROCESSING",
        "SHIPPED",
    ]
    changed_at_values = [event["changed_at"] for event in row_a["status_history"]]
    assert changed_at_values == sorted(changed_at_values)

    row_b = rows[OrderItem.objects.get(product=product_b).id]
    assert row_b["shop"] == {"id": shop_b.id, "name": "Shop B"}
    assert row_b["status"] == "PENDING"
    assert row_b["status_history"] == []


def test_admin_order_item_list_forbidden_for_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.get("/api/admin/order-items")

    assert response.status_code == 403
