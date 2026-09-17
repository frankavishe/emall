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


def test_publish_succeeds_when_all_fields_present(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=False)
    _authenticate(api_client, vendor)

    response = api_client.post(f"/api/vendor/products/{product.id}/publish")

    assert response.status_code == 200
    assert response.data["is_published"] is True
    product.refresh_from_db()
    assert product.is_published is True


def test_publish_rejected_when_a_required_field_is_missing(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=False, price=None)
    _authenticate(api_client, vendor)

    response = api_client.post(f"/api/vendor/products/{product.id}/publish")

    assert response.status_code == 400
    assert "price" in response.data["missing_fields"]
    product.refresh_from_db()
    assert product.is_published is False


def test_unpublish_removes_product_from_public_catalog_without_deleting_it(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    _authenticate(api_client, vendor)

    response = api_client.post(f"/api/vendor/products/{product.id}/unpublish")

    assert response.status_code == 200
    assert response.data["is_published"] is False
    product.refresh_from_db()
    assert product.is_published is False
    assert product.is_deleted is False
