import pytest

from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def _related_ids(api_client, product):
    response = api_client.get(f"/api/catalog/products/{product.id}/related")
    assert response.status_code == 200
    return [item["id"] for item in response.data]


def test_ranks_same_category_then_sibling_category_then_same_shop(api_client):
    parent = CategoryFactory()
    category = CategoryFactory(parent=parent)
    sibling = CategoryFactory(parent=parent)
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, category=category, is_published=True)

    same_shop = ProductFactory(shop=shop, is_published=True)
    in_sibling = ProductFactory(category=sibling, is_published=True)
    in_category = ProductFactory(category=category, is_published=True)
    ProductFactory(is_published=True)  # unrelated

    assert _related_ids(api_client, product) == [in_category.id, in_sibling.id, same_shop.id]


def test_returns_list_item_shape(api_client):
    product = ProductFactory(is_published=True)
    related = ProductFactory(category=product.category, is_published=True)

    response = api_client.get(f"/api/catalog/products/{product.id}/related")

    assert response.data[0]["id"] == related.id
    assert {"name", "price", "thumbnail_url", "shop_name", "in_stock"} <= response.data[0].keys()


def test_excludes_source_and_hidden_products(api_client):
    product = ProductFactory(is_published=True)
    category = product.category
    ProductFactory(category=category, is_published=False)
    ProductFactory(
        category=category, is_published=True, shop=ShopFactory(status=Shop.Status.PENDING)
    )
    deleted = ProductFactory(category=category, is_published=True)
    deleted.is_deleted = True
    deleted.save(update_fields=["is_deleted"])

    assert _related_ids(api_client, product) == []


def test_caps_results_at_eight(api_client):
    product = ProductFactory(is_published=True)
    for _ in range(10):
        ProductFactory(category=product.category, is_published=True)

    assert len(_related_ids(api_client, product)) == 8


def test_returns_404_for_hidden_or_missing_product(api_client):
    hidden = ProductFactory(is_published=False)

    assert api_client.get(f"/api/catalog/products/{hidden.id}/related").status_code == 404
    assert api_client.get("/api/catalog/products/999999/related").status_code == 404
