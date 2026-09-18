import pytest

from apps.accounts.models import User
from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem
from tests.factories import ProductFactory, UserFactory

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


def test_checkout_creates_order_decrements_stock_and_empties_cart(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )

    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["status"] == "PLACED"
    assert response.data["total"] == "19.98"
    assert len(response.data["items"]) == 1
    item = response.data["items"][0]
    assert item["quantity"] == 2
    assert item["unit_price"] == "9.99"
    assert item["subtotal"] == "19.98"
    assert item["status"] == "PENDING"
    assert response.data["payment"]["status"] == "SUCCEEDED"
    assert response.data["shipping"]["postal_code"] == "GA-184-9021"

    order = Order.objects.get(customer=customer)
    assert OrderItem.objects.filter(order=order).count() == 1
    product.refresh_from_db()
    assert product.stock_quantity == 8
    assert CartItem.objects.filter(cart__customer=customer).count() == 0
