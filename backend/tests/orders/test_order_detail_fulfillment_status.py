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


def _place_order(api_client, customer, vendor, quantity=2):
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED, name="Kofi's Electronics")
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
    )
    placed = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    ).data
    return placed["id"]


def test_order_detail_reflects_advanced_line_status_with_no_other_change(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    order_id = _place_order(api_client, customer, vendor)

    _authenticate(api_client, customer)
    before = api_client.get(f"/api/orders/{order_id}").data
    item_before = before["items"][0]
    assert item_before["status"] == "PENDING"

    order_item = OrderItem.objects.get(order_id=order_id)
    advance_order_item_status(order_item=order_item, new_status=OrderItem.Status.PROCESSING)

    after = api_client.get(f"/api/orders/{order_id}").data
    item_after = after["items"][0]

    assert item_after["status"] == "PROCESSING"
    unchanged_fields = {"id", "product", "shop_name", "quantity", "unit_price", "subtotal"}
    for field in unchanged_fields:
        assert item_after[field] == item_before[field]
    assert after["id"] == before["id"]
    assert after["total"] == before["total"]
    assert after["shipping"] == before["shipping"]


@pytest.mark.parametrize("method", ["patch", "post", "delete"])
def test_order_detail_rejects_status_changing_requests_from_customer(api_client, method):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    order_id = _place_order(api_client, customer, vendor)

    _authenticate(api_client, customer)
    response = getattr(api_client, method)(
        f"/api/orders/{order_id}", {"status": "PROCESSING"}, format="json"
    )

    assert response.status_code in (404, 405)
