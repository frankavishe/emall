import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


@pytest.mark.parametrize("new_status", [Shop.Status.PENDING, Shop.Status.REJECTED])
def test_cart_flags_line_unavailable_when_shop_no_longer_approved(api_client, new_status):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")

    product.shop.status = new_status
    product.shop.save(update_fields=["status"])

    response = api_client.get("/api/cart")

    assert response.status_code == 200
    item = response.data["items"][0]
    assert item["is_available"] is False
    assert item["unavailable_reason"] == "shop is no longer approved"
    assert response.data["total"] == "0.00"
