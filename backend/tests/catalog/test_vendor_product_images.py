import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.catalog.models import ProductImage
from apps.catalog.serializers import MAX_PRODUCT_IMAGES
from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def _png(name):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/png")


def _vendor_with_product(api_client, image_count=0):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=False)
    for position in range(image_count):
        ProductImage.objects.create(
            product=product, image=_png(f"seed{position}.png"), position=position
        )
    _authenticate(api_client, vendor)
    return vendor, shop, product


def test_create_with_multiple_images_keeps_all_in_order(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    category = CategoryFactory()
    _authenticate(api_client, vendor)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Three Image Product",
            "description": "x",
            "price": "5.00",
            "stock_quantity": 1,
            "category": category.slug,
            "images": [_png("a.png"), _png("b.png"), _png("c.png")],
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert [image["position"] for image in response.data["images"]] == [0, 1, 2]


def test_patch_appends_images_instead_of_replacing(api_client):
    _, _, product = _vendor_with_product(api_client, image_count=2)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"images": [_png("d.png"), _png("e.png")]},
        format="multipart",
    )

    assert response.status_code == 200
    assert [image["position"] for image in response.data["images"]] == [0, 1, 2, 3]


def test_patch_without_images_leaves_gallery_untouched(api_client):
    _, _, product = _vendor_with_product(api_client, image_count=2)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}", {"price": "9.00"}, format="multipart"
    )

    assert response.status_code == 200
    assert len(response.data["images"]) == 2


def test_patch_removes_only_requested_images_of_this_product(api_client):
    _, _, product = _vendor_with_product(api_client, image_count=3)
    other_product = ProductFactory()
    foreign_image = ProductImage.objects.create(product=other_product, image=_png("f.png"))
    to_remove = product.images.order_by("position").first()

    response = api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"remove_image_ids": [to_remove.id, foreign_image.id]},
        format="multipart",
    )

    assert response.status_code == 200
    remaining_ids = {image["id"] for image in response.data["images"]}
    assert len(remaining_ids) == 2
    assert to_remove.id not in remaining_ids
    assert ProductImage.objects.filter(id=foreign_image.id).exists()


def test_removing_image_keeps_same_named_image_of_another_product(api_client):
    _, _, product = _vendor_with_product(api_client)
    own_image = ProductImage.objects.create(product=product, image=_png("photo.png"))
    other_image = ProductImage.objects.create(product=ProductFactory(), image=_png("photo.png"))
    assert own_image.image.name != other_image.image.name

    api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"remove_image_ids": [own_image.id]},
        format="multipart",
    )

    assert other_image.image.storage.exists(other_image.image.name)


def test_patch_rejects_exceeding_image_limit(api_client):
    _, _, product = _vendor_with_product(api_client, image_count=MAX_PRODUCT_IMAGES)

    response = api_client.patch(
        f"/api/vendor/products/{product.id}",
        {"images": [_png("extra.png")]},
        format="multipart",
    )

    assert response.status_code == 400
    assert "images" in response.data
    assert product.images.count() == MAX_PRODUCT_IMAGES
