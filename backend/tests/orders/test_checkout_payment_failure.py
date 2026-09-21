import pytest

from apps.accounts.models import User
from apps.cart.models import CartItem
from apps.orders.models import Order
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


def test_checkout_declined_payment_leaves_no_order_stock_or_cart_change(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=5)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json"
    )

    response = api_client.post(
        "/api/checkout",
        {"shipping": SHIPPING, "payment_method": "declined"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Payment was declined."
    assert response.data["code"] == "payment_failed"
    assert Order.objects.count() == 0
    product.refresh_from_db()
    assert product.stock_quantity == 5
    assert CartItem.objects.filter(cart__customer=customer).count() == 1


def test_checkout_declined_payment_is_case_insensitive(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=5)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )

    response = api_client.post(
        "/api/checkout",
        {"shipping": SHIPPING, "payment_method": "Declined"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "payment_failed"
