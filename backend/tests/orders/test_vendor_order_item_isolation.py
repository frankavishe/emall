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


def test_patch_on_another_vendors_line_returns_404_with_no_detail_leaked(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)
    shop_a = ShopFactory(owner=vendor_a, status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product_a.id, "quantity": 1}, format="json"
    )
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor_a)
    item_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]

    _authenticate(api_client, vendor_b)
    response_to_real_line = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "PROCESSING"}, format="json"
    )
    response_to_missing_line = api_client.patch(
        "/api/vendor/order-items/999999/status", {"status": "PROCESSING"}, format="json"
    )

    assert response_to_real_line.status_code == 404
    assert response_to_missing_line.status_code == 404
    assert response_to_real_line.data == response_to_missing_line.data


def test_patch_on_own_line_with_non_approved_shop_returns_403(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor)
    item_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]

    shop.status = Shop.Status.REJECTED
    shop.save(update_fields=["status"])

    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "PROCESSING"}, format="json"
    )

    assert response.status_code == 403


def test_one_vendors_line_update_never_affects_another_vendors_line_on_the_same_order(
    api_client,
):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)
    shop_a = ShopFactory(owner=vendor_a, status=Shop.Status.APPROVED)
    shop_b = ShopFactory(owner=vendor_b, status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True, price="9.99", stock_quantity=10)
    product_b = ProductFactory(shop=shop_b, is_published=True, price="5.00", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product_a.id, "quantity": 1}, format="json"
    )
    api_client.post(
        "/api/cart/items", {"product_id": product_b.id, "quantity": 1}, format="json"
    )
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor_b)
    item_b_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]
    before = api_client.get("/api/vendor/order-items").data["results"][0]

    _authenticate(api_client, vendor_a)
    item_a_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]
    advance_response = api_client.patch(
        f"/api/vendor/order-items/{item_a_id}/status", {"status": "PROCESSING"}, format="json"
    )
    assert advance_response.status_code == 200

    _authenticate(api_client, vendor_b)
    after = api_client.get("/api/vendor/order-items").data["results"][0]

    assert after["id"] == item_b_id
    assert after["status"] == before["status"] == "PENDING"
    from apps.orders.models import OrderItemStatusEvent

    assert OrderItemStatusEvent.objects.filter(order_item_id=item_b_id).count() == 0
