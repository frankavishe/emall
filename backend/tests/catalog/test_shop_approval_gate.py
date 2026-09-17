import pytest

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _create_payload(shop, category, name="Gate Test Product"):
    return {
        "shop_id": shop.id,
        "name": name,
        "description": "Should never be created.",
        "price": "9.99",
        "stock_quantity": 5,
        "category": category.slug,
    }


def test_create_and_publish_rejected_for_pending_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.PENDING)
    category = CategoryFactory()
    existing_draft = ProductFactory(shop=shop, is_published=False)
    _authenticate(api_client, vendor)

    create_response = api_client.post(
        "/api/vendor/products", _create_payload(shop, category), format="multipart"
    )
    assert create_response.status_code == 403
    assert not Product.objects.filter(shop=shop, name="Gate Test Product").exists()

    publish_response = api_client.post(f"/api/vendor/products/{existing_draft.id}/publish")
    assert publish_response.status_code == 403
    existing_draft.refresh_from_db()
    assert existing_draft.is_published is False


def test_create_and_publish_rejected_for_rejected_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.REJECTED)
    category = CategoryFactory()
    existing_draft = ProductFactory(shop=shop, is_published=False)
    _authenticate(api_client, vendor)

    create_response = api_client.post(
        "/api/vendor/products", _create_payload(shop, category), format="multipart"
    )
    assert create_response.status_code == 403
    assert not Product.objects.filter(shop=shop, name="Gate Test Product").exists()

    publish_response = api_client.post(f"/api/vendor/products/{existing_draft.id}/publish")
    assert publish_response.status_code == 403
    existing_draft.refresh_from_db()
    assert existing_draft.is_published is False


def test_gate_enforced_per_shop_not_per_account(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    approved_shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    pending_shop = ShopFactory(owner=vendor, status=Shop.Status.PENDING)
    category = CategoryFactory()
    pending_draft = ProductFactory(shop=pending_shop, is_published=False)
    _authenticate(api_client, vendor)

    approved_create = api_client.post(
        "/api/vendor/products",
        _create_payload(approved_shop, category, name="Approved Shop Product"),
        format="multipart",
    )
    assert approved_create.status_code == 201

    pending_create = api_client.post(
        "/api/vendor/products",
        _create_payload(pending_shop, category, name="Pending Shop Product"),
        format="multipart",
    )
    assert pending_create.status_code == 403

    approved_product_id = approved_create.data["id"]
    approved_publish = api_client.post(f"/api/vendor/products/{approved_product_id}/publish")
    assert approved_publish.status_code == 200

    pending_publish = api_client.post(f"/api/vendor/products/{pending_draft.id}/publish")
    assert pending_publish.status_code == 403
