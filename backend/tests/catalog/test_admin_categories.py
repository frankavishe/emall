import pytest

from apps.accounts.models import User
from apps.catalog.models import Category
from tests.factories import CategoryFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def _authenticate(api_client, user):
    response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


@pytest.fixture
def admin(api_client):
    user = UserFactory(role=User.Role.ADMINISTRATOR, is_email_verified=True)
    _authenticate(api_client, user)
    return user


def _create(api_client, name, parent=None):
    return api_client.post(
        "/api/admin/categories", {"name": name, "parent": parent}, format="json"
    )


def test_create_top_level_and_subcategory(api_client, admin):
    top = _create(api_client, "Garden & Outdoor")
    assert top.status_code == 201
    assert top.data["slug"] == "garden-outdoor"
    assert top.data["parent"] is None

    sub = _create(api_client, "Lawn Mowers", top.data["id"])
    assert sub.status_code == 201
    assert sub.data["slug"] == "lawn-mowers"
    assert sub.data["parent"] == top.data["id"]

    tree = api_client.get("/api/admin/categories").data
    garden = next(c for c in tree if c["id"] == top.data["id"])
    assert [c["name"] for c in garden["children"]] == ["Lawn Mowers"]
    assert garden["can_delete"] is False
    assert garden["children"][0]["can_delete"] is True


def test_same_subcategory_name_under_two_parents_gets_distinct_slugs(api_client, admin):
    men = _create(api_client, "Men").data
    women = _create(api_client, "Women").data

    first = _create(api_client, "Shoes", men["id"])
    second = _create(api_client, "Shoes", women["id"])

    assert first.status_code == second.status_code == 201
    assert first.data["slug"] == "shoes"
    assert second.data["slug"] == "women-shoes"


def test_duplicate_name_under_same_parent_rejected(api_client, admin):
    _create(api_client, "Toys")
    response = _create(api_client, "toys")
    assert response.status_code == 400
    assert "name" in response.data


def test_third_level_rejected(api_client, admin):
    top = _create(api_client, "Sports").data
    sub = _create(api_client, "Football", top["id"]).data

    response = _create(api_client, "Boots", sub["id"])

    assert response.status_code == 400
    assert "parent" in response.data


def test_category_with_children_cannot_become_a_subcategory(api_client, admin):
    sports = _create(api_client, "Sports").data
    _create(api_client, "Football", sports["id"])
    other = _create(api_client, "Leisure").data

    response = api_client.patch(
        f"/api/admin/categories/{sports['id']}", {"parent": other["id"]}, format="json"
    )
    assert response.status_code == 400


def test_rename_keeps_slug(api_client, admin):
    category = _create(api_client, "Kitchen").data

    response = api_client.patch(
        f"/api/admin/categories/{category['id']}", {"name": "Kitchenware"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "Kitchenware"
    assert response.data["slug"] == "kitchen"


def test_cannot_add_subcategory_under_parent_with_direct_products(api_client, admin):
    parent = CategoryFactory(name="Gadgets", slug="gadgets")
    ProductFactory(category=parent)

    response = _create(api_client, "Smartwatches", parent.id)

    assert response.status_code == 409
    assert not Category.objects.filter(name="Smartwatches").exists()


def test_delete_rules(api_client, admin):
    parent = _create(api_client, "Music").data
    child = _create(api_client, "Guitars", parent["id"]).data
    used = CategoryFactory(name="Used", slug="used")
    ProductFactory(category=used, is_deleted=True)

    assert api_client.delete(f"/api/admin/categories/{parent['id']}").status_code == 409
    # Soft-deleted products still block deletion.
    assert api_client.delete(f"/api/admin/categories/{used.id}").status_code == 409

    assert api_client.delete(f"/api/admin/categories/{child['id']}").status_code == 204
    assert api_client.delete(f"/api/admin/categories/{parent['id']}").status_code == 204
    assert not Category.objects.filter(pk__in=[parent["id"], child["id"]]).exists()


def test_non_admins_are_forbidden(api_client):
    vendor = UserFactory(is_vendor=True)
    _authenticate(api_client, vendor)
    category = CategoryFactory()

    assert api_client.get("/api/admin/categories").status_code == 403
    assert _create(api_client, "Sneaky").status_code == 403
    assert api_client.delete(f"/api/admin/categories/{category.id}").status_code == 403
    assert Category.objects.filter(pk=category.id).exists()
