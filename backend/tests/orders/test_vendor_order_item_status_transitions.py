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


def _place_order_line(api_client, customer, vendor, quantity=1):
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
    )
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor)
    item_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]
    return item_id, product


def test_vendor_advances_line_through_full_lifecycle(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id, _product = _place_order_line(api_client, customer, vendor)

    for expected_status in ["PROCESSING", "SHIPPED", "DELIVERED"]:
        response = api_client.patch(
            f"/api/vendor/order-items/{item_id}/status",
            {"status": expected_status},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == expected_status
