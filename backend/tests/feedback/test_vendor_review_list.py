import pytest

from apps.accounts.models import User
from apps.feedback.models import Review
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ReviewFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_vendor_sees_reviews_on_their_own_products(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    review = ReviewFactory(product=product, rating=5, comment="Great!")

    _authenticate(api_client, vendor)
    response = api_client.get("/api/vendor/reviews")

    assert response.status_code == 200
    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["id"] == review.id
    assert row["product"]["id"] == product.id
    assert row["product"]["name"] == product.name
    assert row["rating"] == 5
    assert row["comment"] == "Great!"
    assert row["customer_display_name"]
    assert "created_at" in row


def test_vendor_review_list_rejects_non_vendor(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)

    response = api_client.get("/api/vendor/reviews")

    assert response.status_code == 403


def test_vendor_review_list_excludes_other_vendors_products(api_client):
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)
    shop_a = ShopFactory(owner=vendor_a, status=Shop.Status.APPROVED)
    shop_b = ShopFactory(owner=vendor_b, status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True)
    product_b = ProductFactory(shop=shop_b, is_published=True)
    review_a = ReviewFactory(product=product_a)
    ReviewFactory(product=product_b)

    _authenticate(api_client, vendor_a)
    response = api_client.get("/api/vendor/reviews")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == review_a.id


def test_vendor_reviews_endpoint_is_read_only(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    review = ReviewFactory(product=product)

    _authenticate(api_client, vendor)

    assert api_client.patch("/api/vendor/reviews", {}, format="json").status_code == 405
    assert api_client.post("/api/vendor/reviews", {}, format="json").status_code == 405
    assert api_client.delete("/api/vendor/reviews").status_code == 405
    assert Review.objects.filter(pk=review.id).exists()
