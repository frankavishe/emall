import pytest

from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def test_approved_shop_is_public_with_theme(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED, primary_color="#aa3300", accent_color="#ffcc00")

    response = api_client.get(f"/api/catalog/shops/{shop.id}")

    assert response.status_code == 200
    assert response.data == {
        "id": shop.id,
        "name": shop.name,
        "logo_url": None,
        "primary_color": "#aa3300",
        "accent_color": "#ffcc00",
    }


@pytest.mark.parametrize("status", [Shop.Status.PENDING, Shop.Status.REJECTED])
def test_unapproved_shop_is_404(api_client, status):
    shop = ShopFactory(status=status)

    assert api_client.get(f"/api/catalog/shops/{shop.id}").status_code == 404


def test_missing_shop_is_404(api_client):
    assert api_client.get("/api/catalog/shops/999999").status_code == 404


def test_product_detail_includes_shop_theme(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED, primary_color="#123456")
    product = ProductFactory(shop=shop, is_published=True)

    response = api_client.get(f"/api/catalog/products/{product.id}")

    assert response.data["shop"]["primary_color"] == "#123456"
    assert response.data["shop"]["accent_color"] == ""


def test_product_list_filters_by_shop(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    mine = ProductFactory(shop=shop, is_published=True)
    ProductFactory(shop=shop, is_published=False)
    ProductFactory(is_published=True)

    response = api_client.get(f"/api/catalog/products?shop={shop.id}")

    assert [item["id"] for item in response.data["results"]] == [mine.id]


def test_product_list_shop_filter_hides_unapproved_shop(api_client):
    shop = ShopFactory(status=Shop.Status.PENDING)
    ProductFactory(shop=shop, is_published=True)

    response = api_client.get(f"/api/catalog/products?shop={shop.id}")

    assert response.data["results"] == []


def test_product_list_non_numeric_shop_returns_empty(api_client):
    ProductFactory(is_published=True)

    response = api_client.get("/api/catalog/products?shop=abc")

    assert response.status_code == 200
    assert response.data["results"] == []
