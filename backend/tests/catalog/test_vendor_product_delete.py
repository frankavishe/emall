import pytest

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_delete_soft_deletes_and_disappears_from_vendor_list(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop)
    _authenticate(api_client, vendor)

    response = api_client.delete(f"/api/vendor/products/{product.id}")
    assert response.status_code == 204

    # row persists (soft delete), just excluded from the default manager
    assert Product.all_objects.filter(pk=product.id, is_deleted=True).exists()
    assert not Product.objects.filter(pk=product.id).exists()

    list_response = api_client.get("/api/vendor/products")
    assert list_response.status_code == 200
    assert all(item["id"] != product.id for item in list_response.data["results"])


def test_non_owner_cannot_delete_product(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    other_vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=other_vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop)
    _authenticate(api_client, vendor)

    response = api_client.delete(f"/api/vendor/products/{product.id}")
    assert response.status_code == 403
