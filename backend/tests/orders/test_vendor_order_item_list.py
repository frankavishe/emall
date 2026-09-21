import pytest

from apps.accounts.models import User
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


def test_vendor_sees_only_their_own_shops_order_items(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)
    shop_a = ShopFactory(owner=vendor_a, status=Shop.Status.APPROVED)
    shop_b = ShopFactory(owner=vendor_b, status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True, price="9.99", stock_quantity=10)
    product_b = ProductFactory(shop=shop_b, is_published=True, price="5.00", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product_a.id, "quantity": 2}, format="json"
    )
    api_client.post(
        "/api/cart/items", {"product_id": product_b.id, "quantity": 1}, format="json"
    )
    order = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    ).data

    _authenticate(api_client, vendor_a)
    response = api_client.get("/api/vendor/order-items")

    assert response.status_code == 200
    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["product"]["id"] == product_a.id
    assert row["order_id"] == order["id"]
    assert row["quantity"] == 2
    assert row["status"] == "PENDING"
    assert row["shipping"]["recipient_name"] == SHIPPING["recipient_name"]
    assert row["shipping"]["city"] == SHIPPING["city"]


def test_vendor_order_item_list_rejects_non_vendor(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)

    response = api_client.get("/api/vendor/order-items")

    assert response.status_code == 403
