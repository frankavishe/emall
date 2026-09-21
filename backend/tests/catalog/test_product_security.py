import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.catalog.serializers import MAX_PRODUCT_IMAGE_SIZE_BYTES
from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _png_bytes(width=10, height=10):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_create_rejects_non_image_file_disguised_as_image(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    fake_image = SimpleUploadedFile("not-an-image.jpg", b"not actually image bytes", "image/jpeg")

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Bad Upload Product",
            "description": "x",
            "price": "5.00",
            "stock_quantity": 1,
            "category": category.slug,
            "images": [fake_image],
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "images" in response.data


def test_create_rejects_oversized_image(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    oversized = SimpleUploadedFile(
        "big.png",
        b"\x00" * (MAX_PRODUCT_IMAGE_SIZE_BYTES + 1),
        "image/png",
    )

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Oversized Upload Product",
            "description": "x",
            "price": "5.00",
            "stock_quantity": 1,
            "category": category.slug,
            "images": [oversized],
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "images" in response.data


def test_create_accepts_valid_small_image(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    valid_image = SimpleUploadedFile("cable.png", _png_bytes(), "image/png")

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Valid Upload Product",
            "description": "x",
            "price": "5.00",
            "stock_quantity": 1,
            "category": category.slug,
            "images": [valid_image],
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert len(response.data["images"]) == 1


def test_patch_cannot_reassign_product_to_a_different_shop(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    original_shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    other_shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=original_shop, is_published=False)
    _authenticate(api_client, vendor)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"shop_id": other_shop.id, "price": "12.00"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["shop"]["id"] == original_shop.id
    product.refresh_from_db()
    assert product.shop_id == original_shop.id


def test_patch_cannot_reassign_product_to_a_shop_the_vendor_does_not_own(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    other_vendor = UserFactory(role=User.Role.VENDOR)
    original_shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    someone_elses_shop = ShopFactory(owner=other_vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=original_shop, is_published=False)
    _authenticate(api_client, vendor)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"shop_id": someone_elses_shop.id},
        format="json",
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert product.shop_id == original_shop.id
