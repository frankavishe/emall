import pytest

from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory

pytestmark = pytest.mark.django_db


def _shop():
    return ShopFactory(status=Shop.Status.APPROVED)


def test_keyword_filter_matches_name_or_description(api_client):
    shop = _shop()
    ProductFactory(shop=shop, is_published=True, name="USB-C Cable", description="Braided")
    ProductFactory(shop=shop, is_published=True, name="Other Item", description="Has usb-c port")
    ProductFactory(shop=shop, is_published=True, name="Unrelated", description="Nothing here")

    response = api_client.get("/api/catalog/products", {"q": "usb-c"})

    assert response.status_code == 200
    names = {item["name"] for item in response.data["results"]}
    assert names == {"USB-C Cable", "Other Item"}


def test_category_filter_exact_slug(api_client):
    shop = _shop()
    electronics = CategoryFactory(name="Electronics", slug="electronics")
    books = CategoryFactory(name="Books", slug="books")
    ProductFactory(shop=shop, is_published=True, category=electronics, name="Cable")
    ProductFactory(shop=shop, is_published=True, category=books, name="Novel")

    response = api_client.get("/api/catalog/products", {"category": "electronics"})

    assert response.status_code == 200
    names = [item["name"] for item in response.data["results"]]
    assert names == ["Cable"]


def test_price_range_filter_inclusive(api_client):
    shop = _shop()
    ProductFactory(shop=shop, is_published=True, name="Cheap", price="5.00")
    ProductFactory(shop=shop, is_published=True, name="Mid", price="10.00")
    ProductFactory(shop=shop, is_published=True, name="Expensive", price="50.00")

    response = api_client.get(
        "/api/catalog/products", {"min_price": "5.00", "max_price": "10.00"}
    )

    assert response.status_code == 200
    names = {item["name"] for item in response.data["results"]}
    assert names == {"Cheap", "Mid"}


def test_filters_combine(api_client):
    shop = _shop()
    electronics = CategoryFactory(name="Electronics", slug="electronics")
    ProductFactory(
        shop=shop,
        is_published=True,
        category=electronics,
        name="USB-C Cable",
        price="9.99",
    )
    ProductFactory(
        shop=shop,
        is_published=True,
        category=electronics,
        name="USB-C Charger",
        price="25.00",
    )
    ProductFactory(
        shop=shop,
        is_published=True,
        category=electronics,
        name="HDMI Cable",
        price="9.99",
    )

    response = api_client.get(
        "/api/catalog/products",
        {"q": "usb-c", "category": "electronics", "min_price": "0", "max_price": "10.00"},
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.data["results"]]
    assert names == ["USB-C Cable"]
