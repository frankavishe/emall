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


def test_checkout_rejects_line_whose_quantity_now_exceeds_stock(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=5)
    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 5}, format="json"
    )

    # Stock drops after the item was added to the cart (e.g. another order, or a vendor edit).
    product.stock_quantity = 2
    product.save(update_fields=["stock_quantity"])

    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 400
    cart_item = CartItem.objects.get(cart__customer=customer, product=product)
    assert response.data["lines"] == [
        {"cart_item_id": cart_item.id, "reason": "quantity exceeds available stock"}
    ]
    assert Order.objects.count() == 0
    product.refresh_from_db()
    assert product.stock_quantity == 2
    assert CartItem.objects.filter(cart__customer=customer).count() == 1
