import pytest

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_create_product_under_approved_own_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "USB-C Cable",
            "description": "1m braided cable",
            "price": "9.99",
            "stock_quantity": 40,
            "category": category.slug,
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["is_published"] is False
    assert Product.objects.filter(shop=shop, name="USB-C Cable").exists()


def test_create_product_rejected_for_a_shop_the_vendor_does_not_own(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    other_vendor_shop = ShopFactory(status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": other_vendor_shop.id,
            "name": "USB-C Cable",
            "description": "1m braided cable",
            "price": "9.99",
            "stock_quantity": 40,
            "category": category.slug,
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert Product.objects.count() == 0


def test_create_product_rejects_negative_price(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Bad Price",
            "price": "-1.00",
            "stock_quantity": 1,
            "category": category.slug,
        },
        format="multipart",
    )

    assert response.status_code == 400


def test_create_product_rejects_negative_stock(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Bad Stock",
            "price": "1.00",
            "stock_quantity": -1,
            "category": category.slug,
        },
        format="multipart",
    )

    assert response.status_code == 400


def test_create_product_rejects_duplicate_name_in_same_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    payload = {
        "shop_id": shop.id,
        "name": "Same Name",
        "price": "1.00",
        "stock_quantity": 1,
        "category": category.slug,
    }
    first = api_client.post("/api/vendor/products", payload, format="multipart")
    assert first.status_code == 201

    second = api_client.post("/api/vendor/products", payload, format="multipart")
    assert second.status_code == 400
    assert Product.objects.filter(shop=shop, name="Same Name").count() == 1
