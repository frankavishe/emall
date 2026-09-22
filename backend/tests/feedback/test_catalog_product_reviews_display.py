import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ReviewFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_detail_includes_reviews_and_aggregate_for_product_with_reviews(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    reviewer = UserFactory(role=User.Role.CUSTOMER, name="Ama Owusu")
    review = ReviewFactory(
        customer=reviewer, product=product, rating=5, comment="Works great, fast shipping."
    )
    ReviewFactory(product=product, rating=3, comment="")

    response = api_client.get(f"/api/catalog/products/{product.id}")

    assert response.status_code == 200
    body = response.data
    assert body["average_rating"] == 4.0
    assert body["review_count"] == 2
    assert len(body["reviews"]) == 2
    first = next(r for r in body["reviews"] if r["id"] == review.id)
    assert first["rating"] == 5
    assert first["comment"] == "Works great, fast shipping."
    assert first["customer_display_name"]
    assert "created_at" in first


def test_detail_returns_empty_state_for_product_with_no_reviews(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)

    response = api_client.get(f"/api/catalog/products/{product.id}")

    assert response.status_code == 200
    body = response.data
    assert body["average_rating"] is None
    assert body["review_count"] == 0
    assert body["reviews"] == []


def test_list_includes_aggregate_but_not_reviews_array(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    ReviewFactory(product=product, rating=4)

    response = api_client.get("/api/catalog/products")

    assert response.status_code == 200
    result = next(r for r in response.data["results"] if r["id"] == product.id)
    assert result["average_rating"] == 4.0
    assert result["review_count"] == 1
    assert "reviews" not in result


def test_detail_reflects_recalculated_aggregate_after_review_change(api_client):
    shop = ShopFactory(status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    review = ReviewFactory(product=product, rating=2)

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.data["average_rating"] == 2.0
    assert response.data["review_count"] == 1

    review.rating = 4
    review.save(update_fields=["rating"])

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.data["average_rating"] == 4.0
    assert response.data["review_count"] == 1

    review.delete()

    response = api_client.get(f"/api/catalog/products/{product.id}")
    assert response.data["average_rating"] is None
    assert response.data["review_count"] == 0
    assert response.data["reviews"] == []
