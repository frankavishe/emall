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


def _place_order(api_client, price="9.99", quantity=1):
    product = ProductFactory(is_published=True, price=price, stock_quantity=10)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json")
    response = api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    assert response.status_code == 201
    return response.data


def test_order_list_returns_only_own_orders_most_recent_first(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    other_customer = UserFactory(role=User.Role.CUSTOMER)

    _authenticate(api_client, other_customer)
    _place_order(api_client)

    _authenticate(api_client, customer)
    first_order = _place_order(api_client, price="9.99")
    second_order = _place_order(api_client, price="5.00")

    response = api_client.get("/api/orders")

    assert response.status_code == 200
    assert response.data["count"] == 2
    result_ids = [order["id"] for order in response.data["results"]]
    assert result_ids == [second_order["id"], first_order["id"]]


def test_order_list_summary_shape(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)
    order = _place_order(api_client, price="9.99", quantity=2)

    response = api_client.get("/api/orders")

    assert response.status_code == 200
    summary = response.data["results"][0]
    assert summary["id"] == order["id"]
    assert summary["status"] == "PLACED"
    assert summary["total"] == "19.98"
    assert "placed_at" in summary
    assert "items" not in summary
    assert "shipping" not in summary


def test_order_list_requires_authentication(api_client):
    response = api_client.get("/api/orders")

    assert response.status_code == 401


def test_order_list_requires_customer_role(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.get("/api/orders")

    assert response.status_code == 403
