import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.vendors.models import Shop
from apps.vendors.serializers import MAX_SHOP_LOGO_SIZE_BYTES
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _png(name="logo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/png")


def _vendor_with_shop(api_client, status=Shop.Status.PENDING):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=status)
    _authenticate(api_client, vendor)
    return vendor, shop


def _put_logo(api_client, shop, file):
    return api_client.put(f"/api/vendor/shops/{shop.id}/logo", {"logo": file}, format="multipart")


def test_owner_uploads_logo_and_me_includes_it(api_client):
    _, shop = _vendor_with_shop(api_client)

    response = _put_logo(api_client, shop, _png())

    assert response.status_code == 200
    assert response.data["logo_url"].startswith("http")
    assert response.data["status"] == "PENDING"
    me = api_client.get("/api/auth/me")
    assert me.data["shops"][0]["logo_url"] == response.data["logo_url"]


def test_replacing_logo_deletes_old_file(api_client):
    _, shop = _vendor_with_shop(api_client)
    _put_logo(api_client, shop, _png("first.png"))
    shop.refresh_from_db()
    old_name = shop.logo.name

    response = _put_logo(api_client, shop, _png("second.png"))

    assert response.status_code == 200
    shop.refresh_from_db()
    assert shop.logo.name != old_name
    assert not shop.logo.storage.exists(old_name)
    assert shop.logo.storage.exists(shop.logo.name)


def test_delete_clears_logo(api_client):
    _, shop = _vendor_with_shop(api_client)
    _put_logo(api_client, shop, _png())
    shop.refresh_from_db()
    name, storage = shop.logo.name, shop.logo.storage

    response = api_client.delete(f"/api/vendor/shops/{shop.id}/logo")

    assert response.status_code == 200
    assert response.data["logo_url"] is None
    shop.refresh_from_db()
    assert not shop.logo
    assert not storage.exists(name)


def test_approved_shop_stays_approved_after_logo_change(api_client):
    _, shop = _vendor_with_shop(api_client, status=Shop.Status.APPROVED)

    _put_logo(api_client, shop, _png())

    shop.refresh_from_db()
    assert shop.status == Shop.Status.APPROVED


def test_non_owner_cannot_set_logo(api_client):
    other_shop = ShopFactory()
    _authenticate(api_client, UserFactory(role=User.Role.VENDOR))

    response = _put_logo(api_client, other_shop, _png())

    assert response.status_code == 404
    other_shop.refresh_from_db()
    assert not other_shop.logo


def test_unauthenticated_cannot_set_logo(api_client):
    shop = ShopFactory()

    response = _put_logo(api_client, shop, _png())

    assert response.status_code == 401


def test_rejects_oversized_logo(api_client):
    _, shop = _vendor_with_shop(api_client)
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    oversized = SimpleUploadedFile(
        "big.png", buffer.getvalue() + b"\0" * MAX_SHOP_LOGO_SIZE_BYTES, "image/png"
    )

    response = _put_logo(api_client, shop, oversized)

    assert response.status_code == 400
    assert "logo" in response.data


def test_rejects_non_image(api_client):
    _, shop = _vendor_with_shop(api_client)
    not_image = SimpleUploadedFile("logo.png", b"not an image", "image/png")

    response = _put_logo(api_client, shop, not_image)

    assert response.status_code == 400


def test_catalog_exposes_shop_logo(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED, logo=_png())
    product = ProductFactory(shop=shop, is_published=True)

    listing = api_client.get("/api/catalog/products")
    detail = api_client.get(f"/api/catalog/products/{product.id}")

    assert listing.data["results"][0]["shop_logo_url"].endswith(".png")
    assert detail.data["shop"]["logo_url"].endswith(".png")


def test_same_filename_from_two_shops_does_not_collide(api_client):
    _, first_shop = _vendor_with_shop(api_client)
    _put_logo(api_client, first_shop, _png("logo.png"))
    _, second_shop = _vendor_with_shop(api_client)
    _put_logo(api_client, second_shop, _png("logo.png"))

    api_client.delete(f"/api/vendor/shops/{second_shop.id}/logo")

    first_shop.refresh_from_db()
    assert first_shop.logo.storage.exists(first_shop.logo.name)
