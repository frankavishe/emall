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


def test_status_history_only_appears_in_admin_response(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    placed = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    ).data

    order_item = OrderItem.objects.get(product=product)
    advance_order_item_status(order_item=order_item, new_status=OrderItem.Status.PROCESSING)

    _authenticate(api_client, vendor)
    vendor_response = api_client.patch(
        f"/api/vendor/order-items/{order_item.id}/status", {"status": "SHIPPED"}, format="json"
    )
    assert vendor_response.status_code == 200
    assert "status_history" not in vendor_response.data

    vendor_list_response = api_client.get("/api/vendor/order-items")
    assert vendor_list_response.status_code == 200
    assert all("status_history" not in row for row in vendor_list_response.data["results"])

    _authenticate(api_client, customer)
    customer_response = api_client.get(f"/api/orders/{placed['id']}")
    assert customer_response.status_code == 200
    assert all("status_history" not in item for item in customer_response.data["items"])

    _authenticate(api_client, admin)
    admin_response = api_client.get("/api/admin/order-items")
    assert admin_response.status_code == 200
    admin_row = next(
        row for row in admin_response.data["results"] if row["id"] == order_item.id
    )
    assert "status_history" in admin_row
    assert len(admin_row["status_history"]) == 2
