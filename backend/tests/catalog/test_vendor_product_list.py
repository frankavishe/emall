import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_vendor_only_sees_products_from_shops_they_own(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop_a = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    shop_b = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    other_vendor_shop = ShopFactory(status=Shop.Status.APPROVED)

    product_a = ProductFactory(shop=shop_a, name="A")
    product_b = ProductFactory(shop=shop_b, name="B")
    ProductFactory(shop=other_vendor_shop, name="Not Mine")

    _authenticate(api_client, vendor)
    response = api_client.get("/api/vendor/products")

    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.data["results"]}
    assert returned_ids == {product_a.id, product_b.id}
