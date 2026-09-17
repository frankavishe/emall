import pytest

from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def test_out_of_stock_product_still_appears_in_list_and_detail(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(
        shop=shop, is_published=True, name="Sold Out Item", stock_quantity=0
    )

    list_response = api_client.get("/api/catalog/products")
    assert list_response.status_code == 200
    item = next(r for r in list_response.data["results"] if r["id"] == product.id)
    assert item["in_stock"] is False

    detail_response = api_client.get(f"/api/catalog/products/{product.id}")
    assert detail_response.status_code == 200
    assert detail_response.data["stock_status"] == "out_of_stock"
