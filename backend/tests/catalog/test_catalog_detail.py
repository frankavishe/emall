import pytest

from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def test_detail_returns_full_shape(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED, name="Kofi's Electronics")
    product = ProductFactory(shop=shop, is_published=True, name="USB-C Cable", price="9.99")

    response = api_client.get(f"/api/catalog/products/{product.id}")

    assert response.status_code == 200
    body = response.data
    assert body["id"] == product.id
    assert body["name"] == "USB-C Cable"
    assert body["price"] == "9.99"
    assert body["category"]["slug"] == product.category.slug
    assert body["stock_status"] == "in_stock"
    assert body["shop"] == {"id": shop.id, "name": "Kofi's Electronics"}
    assert body["images"] == []


def test_detail_returns_404_for_nonexistent_product(api_client):
    response = api_client.get("/api/catalog/products/999999")
    assert response.status_code == 404


def test_detail_returns_404_for_unpublished_product(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=False)

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.status_code == 404


def test_detail_returns_404_for_soft_deleted_product(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    product.is_deleted = True
    product.save(update_fields=["is_deleted"])

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.status_code == 404


def test_detail_returns_404_for_non_approved_shop(api_client):
    shop = ShopFactory(status=Shop.Status.PENDING)
    product = ProductFactory(shop=shop, is_published=True)

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.status_code == 404
