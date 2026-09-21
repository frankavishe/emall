import pytest
from django.urls import Resolver404, resolve

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


def _place_order_line(api_client, customer, vendor):
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    return product


@pytest.mark.parametrize("method", ["patch", "post", "delete", "put"])
def test_admin_order_item_list_endpoint_is_read_only(api_client, method):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    _place_order_line(api_client, customer, vendor)

    _authenticate(api_client, admin)
    response = getattr(api_client, method)(
        "/api/admin/order-items", {"status": "PROCESSING"}, format="json"
    )

    assert response.status_code in (404, 405)


def test_admin_order_item_detail_path_does_not_exist():
    """No `/api/admin/order-items/{id}` route is registered at all — oversight is list-only
    (FR-008), so no mutation (or even a read) is possible there for any HTTP verb. Resolved at
    the URL-resolver level, not via the test client: a `Client` request to an unmatched URL hits
    Django's technical-404 template renderer, which crashes under this environment's Django
    5.1/Python 3.14 combination (`Context.__copy__` inside the test client's render-instrumentation
    signal handler) — unrelated to this feature's app code."""
    with pytest.raises(Resolver404):
        resolve("/api/admin/order-items/11")
