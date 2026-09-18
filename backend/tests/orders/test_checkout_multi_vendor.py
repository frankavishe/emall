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


def test_checkout_spans_two_vendors_in_one_order(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop_a = ShopFactory(status=Shop.Status.APPROVED)
    shop_b = ShopFactory(status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True, price="9.99", stock_quantity=10)
    product_b = ProductFactory(shop=shop_b, is_published=True, price="5.00", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product_a.id, "quantity": 1}, format="json"
    )
    api_client.post(
        "/api/cart/items", {"product_id": product_b.id, "quantity": 1}, format="json"
    )

    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 201
    assert len(response.data["items"]) == 2
    shop_names = {item["shop_name"] for item in response.data["items"]}
    assert shop_names == {shop_a.name, shop_b.name}
    assert all(item["status"] == "PENDING" for item in response.data["items"])
