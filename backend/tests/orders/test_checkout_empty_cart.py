import pytest

from apps.accounts.models import User
from apps.orders.models import Order
from tests.factories import UserFactory

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


def test_checkout_rejects_empty_cart(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)

    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Your cart is empty."
    assert Order.objects.count() == 0
