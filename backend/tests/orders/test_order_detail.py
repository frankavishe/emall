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


def test_order_detail_returns_full_shape(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory(status=Shop.Status.APPROVED, name="Kofi's Electronics")
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    placed = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    ).data

    response = api_client.get(f"/api/orders/{placed['id']}")

    assert response.status_code == 200
    assert response.data["id"] == placed["id"]
    assert response.data["status"] == "PLACED"
    assert response.data["total"] == "19.98"
    assert response.data["shipping"]["recipient_name"] == "Ama Owusu"
    assert response.data["shipping"]["postal_code"] == "GA-184-9021"
    assert len(response.data["items"]) == 1
    item = response.data["items"][0]
    assert item["product"]["id"] == product.id
    assert item["shop_name"] == "Kofi's Electronics"
    assert item["quantity"] == 2
    assert item["unit_price"] == "9.99"
    assert item["subtotal"] == "19.98"
    assert item["status"] == "PENDING"
    assert response.data["payment"]["method"] == "card"
    assert response.data["payment"]["status"] == "SUCCEEDED"


def test_order_detail_nonexistent_id_returns_404(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)

    response = api_client.get("/api/orders/999999")

    assert response.status_code == 404
