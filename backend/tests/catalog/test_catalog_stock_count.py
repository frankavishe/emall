import pytest

from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("stock", "low_stock"), [(0, False), (1, True), (5, True), (6, False)]
)
def test_list_shows_stock_count_and_low_stock_flag(api_client, settings, stock, low_stock):
    settings.LOW_STOCK_THRESHOLD = 5
    product = ProductFactory(shop=ShopFactory(status=Shop.Status.APPROVED), is_published=True, stock_quantity=stock)

    response = api_client.get("/api/catalog/products")

    item = next(p for p in response.data["results"] if p["id"] == product.id)
    assert item["stock_quantity"] == stock
    assert item["low_stock"] is low_stock
