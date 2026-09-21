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
    return item_id


def _advance(api_client, item_id, new_status):
    return api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": new_status}, format="json"
    )


def _current_status(api_client, item_id):
    results = api_client.get("/api/vendor/order-items").data["results"]
    return next(row for row in results if row["id"] == item_id)["status"]


def test_skipping_a_step_is_rejected_and_status_unchanged(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id = _place_order_line(api_client, customer, vendor)

    response = _advance(api_client, item_id, "DELIVERED")

    assert response.status_code == 400
    assert _current_status(api_client, item_id) == "PENDING"


def test_backward_transition_is_rejected_and_status_unchanged(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id = _place_order_line(api_client, customer, vendor)
    _advance(api_client, item_id, "PROCESSING")

    response = _advance(api_client, item_id, "PENDING")

    assert response.status_code == 400
    assert _current_status(api_client, item_id) == "PROCESSING"


def test_transition_from_delivered_terminal_state_is_rejected(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id = _place_order_line(api_client, customer, vendor)
    _advance(api_client, item_id, "PROCESSING")
    _advance(api_client, item_id, "SHIPPED")
    _advance(api_client, item_id, "DELIVERED")

    response = _advance(api_client, item_id, "PROCESSING")

    assert response.status_code == 400
    assert _current_status(api_client, item_id) == "DELIVERED"


def test_transition_from_cancelled_terminal_state_is_rejected(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id = _place_order_line(api_client, customer, vendor)
    _advance(api_client, item_id, "CANCELLED")

    response = _advance(api_client, item_id, "PROCESSING")

    assert response.status_code == 400
    assert _current_status(api_client, item_id) == "CANCELLED"


def test_cancellation_not_reachable_once_shipped(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id = _place_order_line(api_client, customer, vendor)
    _advance(api_client, item_id, "PROCESSING")
    _advance(api_client, item_id, "SHIPPED")

    response = _advance(api_client, item_id, "CANCELLED")

    assert response.status_code == 400
    assert _current_status(api_client, item_id) == "SHIPPED"
