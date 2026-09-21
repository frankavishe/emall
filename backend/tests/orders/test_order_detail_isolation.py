import pytest

from apps.accounts.models import User
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


def test_order_detail_for_another_customers_order_returns_404_indistinguishable_from_missing(
    api_client,
):
    owner = UserFactory(role=User.Role.CUSTOMER)
    other_customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, owner)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    owners_order = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    ).data

    _authenticate(api_client, other_customer)
    response_to_real_order = api_client.get(f"/api/orders/{owners_order['id']}")
    response_to_missing_order = api_client.get("/api/orders/999999")

    assert response_to_real_order.status_code == 404
    assert response_to_missing_order.status_code == 404
    assert response_to_real_order.data == response_to_missing_order.data
