import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import CategoryFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def test_public_category_list_is_a_tree(api_client):
    electronics = CategoryFactory(name="Electronics", slug="electronics")
    CategoryFactory(name="Phones", slug="phones", parent=electronics)
    CategoryFactory(name="Laptops", slug="laptops", parent=electronics)
    CategoryFactory(name="Books", slug="books")

    response = api_client.get("/api/catalog/categories")

    assert response.status_code == 200
    by_slug = {c["slug"]: c for c in response.data}
    assert "phones" not in by_slug
    assert [c["slug"] for c in by_slug["electronics"]["children"]] == ["laptops", "phones"]
    assert by_slug["books"]["children"] == []


def test_parent_filter_includes_subcategory_products(api_client):
    electronics = CategoryFactory(name="Electronics", slug="electronics")
    phones = CategoryFactory(name="Phones", slug="phones", parent=electronics)
    books = CategoryFactory(name="Books", slug="books")
    shop = ShopFactory(status=Shop.Status.APPROVED)
    ProductFactory(shop=shop, category=phones, is_published=True, name="Phone")
    ProductFactory(shop=shop, category=books, is_published=True, name="Novel")

    parent = api_client.get("/api/catalog/products", {"category": "electronics"}).data
    assert [p["name"] for p in parent["results"]] == ["Phone"]
    child = api_client.get("/api/catalog/products", {"category": "phones"}).data
    assert [p["name"] for p in child["results"]] == ["Phone"]


@pytest.fixture
def vendor_client(api_client):
    vendor = UserFactory(role=User.Role.VENDOR, is_email_verified=True)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    response = api_client.post(
        "/api/auth/login", {"email": vendor.email, "password": PASSWORD}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client, shop


def test_vendor_must_pick_subcategory_when_parent_has_children(vendor_client):
    api_client, shop = vendor_client
    electronics = CategoryFactory(name="Electronics", slug="electronics")
    CategoryFactory(name="Phones", slug="phones", parent=electronics)
    CategoryFactory(name="Books", slug="books")

    rejected = api_client.post(
        "/api/vendor/products",
        {"shop_id": shop.id, "name": "Thing", "category": "electronics"},
        format="json",
    )
    assert rejected.status_code == 400
    assert "Choose a subcategory of Electronics" in str(rejected.data["category"])

    for slug, name in (("phones", "Phone"), ("books", "Novel")):
        accepted = api_client.post(
            "/api/vendor/products",
            {"shop_id": shop.id, "name": name, "category": slug},
            format="json",
        )
        assert accepted.status_code == 201, accepted.data
