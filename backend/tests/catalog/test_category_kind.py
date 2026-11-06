import pytest

from apps.accounts.models import User
from apps.catalog.models import Category
from apps.vendors.models import Shop
from tests.factories import (
    CategoryFactory,
    ProductFactory,
    ServiceCategoryFactory,
    ServiceFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(api_client):
    api_client.force_authenticate(user=UserFactory(role=User.Role.ADMINISTRATOR))
    return api_client


def _slugs(response):
    return {category["slug"] for category in response.data}


def test_public_list_defaults_to_product_categories(api_client):
    product = CategoryFactory()
    service = ServiceCategoryFactory()

    slugs = _slugs(api_client.get("/api/catalog/categories"))

    assert product.slug in slugs
    assert service.slug not in slugs


def test_public_list_can_ask_for_service_categories(api_client):
    product = CategoryFactory()
    service = ServiceCategoryFactory()

    slugs = _slugs(api_client.get("/api/catalog/categories?kind=SERVICE"))

    assert service.slug in slugs
    assert product.slug not in slugs


def test_unknown_kind_returns_nothing(api_client):
    CategoryFactory()

    assert api_client.get("/api/catalog/categories?kind=NOPE").data == []


def test_admin_creates_a_service_category(admin_client):
    response = admin_client.post(
        "/api/admin/categories", {"name": "Hair care", "kind": "SERVICE"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["kind"] == "SERVICE"
    assert response.data["service_count"] == 0


def test_admin_category_defaults_to_product(admin_client):
    response = admin_client.post("/api/admin/categories", {"name": "Tools"}, format="json")

    assert response.status_code == 201
    assert response.data["kind"] == "PRODUCT"


def test_subcategory_takes_its_parents_kind_whatever_is_sent(admin_client):
    parent = ServiceCategoryFactory()

    response = admin_client.post(
        "/api/admin/categories",
        {"name": "Braids", "parent": parent.id, "kind": "PRODUCT"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["kind"] == "SERVICE"


def test_same_top_level_name_can_exist_once_per_kind(admin_client):
    url = "/api/admin/categories"

    first = admin_client.post(url, {"name": "Beauty care", "kind": "PRODUCT"}, format="json")
    second = admin_client.post(url, {"name": "Beauty care", "kind": "SERVICE"}, format="json")
    third = admin_client.post(url, {"name": "Beauty care", "kind": "SERVICE"}, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data["slug"] != second.data["slug"]
    assert third.status_code == 400


def test_unused_category_can_change_kind(admin_client):
    category = CategoryFactory()

    response = admin_client.patch(
        f"/api/admin/categories/{category.id}", {"kind": "SERVICE"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["kind"] == "SERVICE"


def test_category_in_use_cannot_change_kind(admin_client):
    with_product = ProductFactory().category
    with_service = ServiceFactory().category
    with_child = CategoryFactory()
    CategoryFactory(parent=with_child)

    for category, kind in (
        (with_product, "SERVICE"),
        (with_service, "PRODUCT"),
        (with_child, "SERVICE"),
    ):
        response = admin_client.patch(
            f"/api/admin/categories/{category.id}", {"kind": kind}, format="json"
        )
        assert response.status_code == 409
        kept = Category.objects.get(pk=category.pk)
        assert kept.kind == category.kind


def test_category_with_a_service_cannot_be_deleted(admin_client):
    category = ServiceFactory().category

    response = admin_client.delete(f"/api/admin/categories/{category.id}")

    assert response.status_code == 409
    assert Category.objects.filter(pk=category.pk).exists()


def test_archived_service_still_blocks_deletion(admin_client):
    category = ServiceFactory(is_archived=True, is_published=False).category

    assert admin_client.delete(f"/api/admin/categories/{category.id}").status_code == 409


def test_category_with_a_service_cannot_gain_a_subcategory(admin_client):
    category = ServiceFactory().category

    response = admin_client.post(
        "/api/admin/categories", {"name": "Child", "parent": category.id}, format="json"
    )

    assert response.status_code == 409


def test_admin_tree_counts_services_and_blocks_delete(admin_client):
    category = ServiceFactory().category

    response = admin_client.get("/api/admin/categories")

    row = next(item for item in response.data if item["id"] == category.id)
    assert row["service_count"] == 1
    assert row["product_count"] == 0
    assert row["can_delete"] is False


def test_product_cannot_use_a_service_category(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    api_client.force_authenticate(user=shop.owner)

    response = api_client.post(
        "/api/vendor/products",
        {"shop_id": shop.id, "name": "Comb", "category": ServiceCategoryFactory().slug},
        format="json",
    )

    assert response.status_code == 400
    assert "category" in response.data
