import pytest

from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def test_list_returns_only_published_approved_shop_products(api_client):
    approved_shop = ShopFactory(status=Shop.Status.APPROVED)
    pending_shop = ShopFactory(status=Shop.Status.PENDING)

    visible = ProductFactory(shop=approved_shop, is_published=True, name="Visible Product")
    ProductFactory(shop=approved_shop, is_published=False, name="Unpublished Product")
    ProductFactory(shop=pending_shop, is_published=True, name="Pending Shop Product")
    deleted = ProductFactory(shop=approved_shop, is_published=True, name="Deleted Product")
    deleted.is_deleted = True
    deleted.save(update_fields=["is_deleted"])

    response = api_client.get("/api/catalog/products")

    assert response.status_code == 200
    names = [item["name"] for item in response.data["results"]]
    assert names == [visible.name]


def test_list_search_with_no_matches_returns_empty_results_not_error(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    ProductFactory(shop=shop, is_published=True, name="Something Else")

    response = api_client.get("/api/catalog/products", {"q": "no-such-keyword-anywhere"})

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []
