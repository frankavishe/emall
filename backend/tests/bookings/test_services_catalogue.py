"""Who can list services, and what the public sees."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.bookings.models import OpeningHours, Service, ShopClosure
from apps.vendors.models import Shop
from tests.factories import (
    CategoryFactory,
    OpeningHoursFactory,
    ServiceCategoryFactory,
    ServiceFactory,
    ServicesShopFactory,
    ShopClosureFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def _vendor():
    return UserFactory(role=User.Role.VENDOR)


def _payload(shop, category, **overrides):
    return {
        "shop_id": shop.id,
        "name": "Haircut",
        "description": "A trim.",
        "price": "15000.00",
        "duration_minutes": 60,
        "category": category.slug,
        **overrides,
    }


def _as(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# --- Creating and changing services -------------------------------------------


def test_owner_of_an_approved_services_shop_creates_a_draft(api_client):
    shop = ServicesShopFactory()
    category = ServiceCategoryFactory()

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services", _payload(shop, category), format="json"
    )

    assert response.status_code == 201
    assert response.data["is_published"] is False
    assert response.data["category"] == category.slug
    assert response.data["category_name"] == category.name
    service = Service.objects.get(pk=response.data["id"])
    assert service.price == Decimal("15000.00")
    assert AuditEvent.objects.filter(action=AuditAction.SERVICE_CREATED).count() == 1


@pytest.mark.parametrize("status", [Shop.Status.PENDING, Shop.Status.REJECTED])
def test_unapproved_shop_cannot_create_a_service(api_client, status):
    shop = ServicesShopFactory(status=status)

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services", _payload(shop, ServiceCategoryFactory()), format="json"
    )

    assert response.status_code == 403
    assert not Service.objects.exists()


@pytest.mark.parametrize("status", [Shop.Status.PENDING, Shop.Status.REJECTED])
def test_unapproved_shop_cannot_change_or_publish_a_service(api_client, status):
    service = ServiceFactory(shop__status=status, is_published=False)
    client = _as(api_client, service.shop.owner)

    url = f"/api/vendor/services/{service.id}"
    assert client.patch(url, {"name": "New"}, format="json").status_code == 403
    assert client.post(f"{url}/publish").status_code == 403
    assert client.delete(url).status_code == 403


def test_goods_shop_cannot_create_a_service(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services", _payload(shop, ServiceCategoryFactory()), format="json"
    )

    assert response.status_code == 403


def test_cannot_create_a_service_in_someone_elses_shop(api_client):
    shop = ServicesShopFactory()

    response = _as(api_client, _vendor()).post(
        "/api/vendor/services", _payload(shop, ServiceCategoryFactory()), format="json"
    )

    assert response.status_code == 403


def test_customer_cannot_create_a_service(api_client):
    shop = ServicesShopFactory()
    customer = UserFactory(role=User.Role.CUSTOMER)

    response = _as(api_client, customer).post(
        "/api/vendor/services", _payload(shop, ServiceCategoryFactory()), format="json"
    )

    assert response.status_code == 403


def test_a_product_category_is_refused(api_client):
    shop = ServicesShopFactory()

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services", _payload(shop, CategoryFactory()), format="json"
    )

    assert response.status_code == 400
    assert "category" in response.data


def test_a_category_with_subcategories_is_refused(api_client):
    shop = ServicesShopFactory()
    parent = ServiceCategoryFactory()
    ServiceCategoryFactory(parent=parent)

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services", _payload(shop, parent), format="json"
    )

    assert response.status_code == 400
    assert "category" in response.data


@pytest.mark.parametrize(
    "field, value",
    [
        ("price", "0"),
        ("price", "-1"),
        ("duration_minutes", 0),
        ("duration_minutes", 45),
        ("duration_minutes", 1470),
        ("name", ""),
    ],
)
def test_invalid_service_fields_are_refused(api_client, field, value):
    shop = ServicesShopFactory()

    response = _as(api_client, shop.owner).post(
        "/api/vendor/services",
        _payload(shop, ServiceCategoryFactory(), **{field: value}),
        format="json",
    )

    assert response.status_code == 400
    assert field in response.data


def test_name_must_be_unique_within_a_shop_but_an_archived_name_is_free(api_client):
    existing = ServiceFactory(name="Haircut")
    client = _as(api_client, existing.shop.owner)
    payload = _payload(existing.shop, ServiceCategoryFactory())

    assert client.post("/api/vendor/services", payload, format="json").status_code == 400

    assert client.delete(f"/api/vendor/services/{existing.id}").status_code == 204
    assert client.post("/api/vendor/services", payload, format="json").status_code == 201


def test_owner_edits_a_service_but_not_its_shop(api_client):
    service = ServiceFactory()
    other_shop = ServicesShopFactory(owner=service.shop.owner)
    original_shop_id = service.shop_id

    response = _as(api_client, service.shop.owner).patch(
        f"/api/vendor/services/{service.id}",
        {"price": "30000.00", "shop_id": other_shop.id},
        format="json",
    )

    assert response.status_code == 200
    service.refresh_from_db()
    assert service.price == Decimal("30000.00")
    assert service.shop_id == original_shop_id


def test_other_owners_get_404(api_client):
    service = ServiceFactory()
    client = _as(api_client, _vendor())

    url = f"/api/vendor/services/{service.id}"
    assert client.get(url).status_code == 404
    assert client.patch(url, {"name": "Mine"}, format="json").status_code == 404
    assert client.delete(url).status_code == 404
    assert client.post(f"{url}/publish").status_code == 404
    assert client.post(f"{url}/unpublish").status_code == 404


def test_vendor_list_shows_only_their_unarchived_services(api_client):
    mine = ServiceFactory()
    ServiceFactory(shop=mine.shop, is_archived=True, is_published=False)
    ServiceFactory()

    response = _as(api_client, mine.shop.owner).get("/api/vendor/services")

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [mine.id]


# --- Publishing ---------------------------------------------------------------


def test_publish_needs_a_shop_location(api_client):
    service = ServiceFactory(shop__latitude=None, shop__longitude=None, is_published=False)

    response = _as(api_client, service.shop.owner).post(
        f"/api/vendor/services/{service.id}/publish"
    )

    assert response.status_code == 400
    assert "location" in response.data["detail"]
    service.refresh_from_db()
    assert service.is_published is False


def test_publish_and_unpublish(api_client):
    service = ServiceFactory(is_published=False)
    client = _as(api_client, service.shop.owner)

    response = client.post(f"/api/vendor/services/{service.id}/publish")
    assert response.status_code == 200
    assert response.data["is_published"] is True

    response = client.post(f"/api/vendor/services/{service.id}/unpublish")
    assert response.status_code == 200
    assert response.data["is_published"] is False


def test_archive_unpublishes_and_keeps_the_row(api_client):
    service = ServiceFactory()

    response = _as(api_client, service.shop.owner).delete(f"/api/vendor/services/{service.id}")

    assert response.status_code == 204
    service.refresh_from_db()
    assert service.is_archived is True
    assert service.is_published is False


# --- Public browsing ----------------------------------------------------------


def test_public_list_shows_only_published_services_of_approved_shops(api_client):
    visible = ServiceFactory()
    ServiceFactory(is_published=False)
    ServiceFactory(is_archived=True)
    ServiceFactory(shop__status=Shop.Status.PENDING)
    ServiceFactory(shop__status=Shop.Status.REJECTED)

    response = api_client.get("/api/catalog/services")

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [visible.id]
    item = response.data["results"][0]
    assert item["name"] == visible.name
    assert item["duration_minutes"] == 60
    assert item["category"] == visible.category.name
    assert item["category_slug"] == visible.category.slug
    assert item["shop"]["id"] == visible.shop_id
    assert item["shop"]["business_type"] == "SERVICES"


def test_public_list_filters_by_search_shop_and_category(api_client):
    parent = ServiceCategoryFactory()
    child = ServiceCategoryFactory(parent=parent)
    haircut = ServiceFactory(name="Haircut", category=child)
    oil = ServiceFactory(name="Oil change", description="Engine care")

    def ids(query):
        response = api_client.get(f"/api/catalog/services?{query}")
        assert response.status_code == 200
        return [item["id"] for item in response.data["results"]]

    assert ids("search=haircut") == [haircut.id]
    assert ids("search=engine") == [oil.id]
    assert ids(f"shop={oil.shop_id}") == [oil.id]
    assert ids("shop=not-a-number") == []
    assert ids(f"category={child.slug}") == [haircut.id]
    # A top-level category includes its subcategories.
    assert ids(f"category={parent.slug}") == [haircut.id]


def test_public_list_is_paginated(api_client):
    response = api_client.get("/api/catalog/services")

    assert set(response.data) == {"count", "next", "previous", "results"}


@pytest.mark.parametrize(
    "overrides",
    [{"is_published": False}, {"is_archived": True}, {"shop__status": Shop.Status.PENDING}],
)
def test_public_detail_is_404_for_hidden_services(api_client, overrides):
    service = ServiceFactory(**overrides)

    assert api_client.get(f"/api/catalog/services/{service.id}").status_code == 404


def test_public_detail(api_client):
    service = ServiceFactory()

    response = api_client.get(f"/api/catalog/services/{service.id}")

    assert response.status_code == 200
    assert response.data["id"] == service.id


def test_shop_directory_counts_visible_services_without_multiplying_products(api_client):
    from tests.factories import ProductFactory

    shop = ShopFactory(status=Shop.Status.APPROVED)
    ProductFactory(shop=shop, is_published=True)
    ProductFactory(shop=shop, is_published=True)
    # Not realistic for one shop, but it proves the two counts don't multiply each other.
    ServiceFactory(shop=shop)
    ServiceFactory(shop=shop)
    ServiceFactory(shop=shop)
    ServiceFactory(shop=shop, is_published=False)

    response = api_client.get("/api/catalog/shops")

    row = next(item for item in response.data["results"] if item["id"] == shop.id)
    assert row["product_count"] == 2
    assert row["service_count"] == 3


# --- Schedule and closures ------------------------------------------------------


def _schedule(capacity=2, hours=None):
    return {
        "booking_capacity": capacity,
        "hours": hours
        if hours is not None
        else [
            {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"},
            {"weekday": 0, "opens_at": "13:00", "closes_at": "17:00"},
        ],
    }


def test_owner_replaces_hours_and_capacity(api_client):
    shop = ServicesShopFactory()
    OpeningHoursFactory(shop=shop, weekday=3)
    client = _as(api_client, shop.owner)

    response = client.put(f"/api/vendor/shops/{shop.id}/schedule", _schedule(), format="json")

    assert response.status_code == 200
    assert response.data["booking_capacity"] == 2
    assert response.data["hours"][0] == {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"}
    shop.refresh_from_db()
    assert shop.booking_capacity == 2
    assert OpeningHours.objects.filter(shop=shop).count() == 2
    assert not OpeningHours.objects.filter(shop=shop, weekday=3).exists()
    assert client.get(f"/api/vendor/shops/{shop.id}/schedule").data == response.data
    assert AuditEvent.objects.filter(action=AuditAction.SHOP_SCHEDULE_UPDATED).count() == 1


@pytest.mark.parametrize(
    "schedule",
    [
        _schedule(capacity=0),
        _schedule(hours=[{"weekday": 7, "opens_at": "09:00", "closes_at": "12:00"}]),
        _schedule(hours=[{"weekday": 0, "opens_at": "12:00", "closes_at": "12:00"}]),
        _schedule(hours=[{"weekday": 0, "opens_at": "13:00", "closes_at": "09:00"}]),
        _schedule(
            hours=[
                {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"},
                {"weekday": 0, "opens_at": "11:00", "closes_at": "14:00"},
            ]
        ),
    ],
)
def test_invalid_schedules_are_refused_and_keep_the_old_hours(api_client, schedule):
    shop = ServicesShopFactory()
    OpeningHoursFactory(shop=shop, weekday=3)

    response = _as(api_client, shop.owner).put(
        f"/api/vendor/shops/{shop.id}/schedule", schedule, format="json"
    )

    assert response.status_code == 400
    assert OpeningHours.objects.filter(shop=shop, weekday=3).exists()


def test_touching_periods_are_allowed(api_client):
    shop = ServicesShopFactory()

    response = _as(api_client, shop.owner).put(
        f"/api/vendor/shops/{shop.id}/schedule",
        _schedule(
            hours=[
                {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"},
                {"weekday": 0, "opens_at": "12:00", "closes_at": "14:00"},
            ]
        ),
        format="json",
    )

    assert response.status_code == 200


def test_schedule_is_limited_to_the_owner_of_an_approved_services_shop(api_client):
    url = "/api/vendor/shops/{}/schedule"
    pending = ServicesShopFactory(status=Shop.Status.PENDING)
    goods = ShopFactory(status=Shop.Status.APPROVED)
    other = ServicesShopFactory()

    client = _as(api_client, pending.owner)
    response = client.put(url.format(pending.id), _schedule(), format="json")
    assert response.status_code == 403

    response = _as(api_client, goods.owner).put(url.format(goods.id), _schedule(), format="json")
    assert response.status_code == 403
    assert api_client.get(url.format(goods.id)).status_code == 403

    response = api_client.get(url.format(other.id))
    assert response.status_code == 404
    response = api_client.put(url.format(other.id), _schedule(), format="json")
    assert response.status_code == 404


def test_owner_adds_lists_and_removes_closures(api_client):
    shop = ServicesShopFactory()
    client = _as(api_client, shop.owner)
    tomorrow = (timezone.now() + timedelta(days=2)).date().isoformat()
    url = f"/api/vendor/shops/{shop.id}/closures"

    response = client.post(url, {"date": tomorrow, "note": "Holiday"}, format="json")
    assert response.status_code == 201
    closure_id = response.data["id"]

    # The same date twice is refused.
    assert client.post(url, {"date": tomorrow}, format="json").status_code == 400

    listing = client.get(url)
    assert listing.status_code == 200
    assert listing.data["results"] == [{"id": closure_id, "date": tomorrow, "note": "Holiday"}]

    assert client.delete(f"{url}/{closure_id}").status_code == 204
    assert not ShopClosure.objects.exists()


def test_closure_in_the_past_is_refused_and_past_closures_are_not_listed(api_client):
    shop = ServicesShopFactory()
    client = _as(api_client, shop.owner)
    url = f"/api/vendor/shops/{shop.id}/closures"
    past = (timezone.now() - timedelta(days=3)).date()
    ShopClosureFactory(shop=shop, date=past)

    assert client.post(url, {"date": past.isoformat()}, format="json").status_code == 400
    assert client.get(url).data["results"] == []


def test_closures_are_limited_to_the_owner(api_client):
    closure = ShopClosureFactory()
    client = _as(api_client, _vendor())
    url = f"/api/vendor/shops/{closure.shop_id}/closures"

    assert client.get(url).status_code == 404
    assert client.post(url, {"date": "2031-01-01"}, format="json").status_code == 404
    assert client.delete(f"{url}/{closure.id}").status_code == 404
    assert ShopClosure.objects.filter(pk=closure.pk).exists()
