import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ReviewFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_admin_sees_every_review_across_shops(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    shop_a = ShopFactory(status=Shop.Status.APPROVED, name="Kofi's Electronics")
    shop_b = ShopFactory(status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True)
    product_b = ProductFactory(shop=shop_b, is_published=True)
    reviewer = UserFactory(role=User.Role.CUSTOMER, email="ama@example.com")
    review_a = ReviewFactory(customer=reviewer, product=product_a, rating=5)
    ReviewFactory(product=product_b, rating=3)

    _authenticate(api_client, admin)
    response = api_client.get("/api/admin/reviews")

    assert response.status_code == 200
    assert response.data["count"] == 2
    row = next(r for r in response.data["results"] if r["id"] == review_a.id)
    assert row["product"]["id"] == product_a.id
    assert row["shop"]["id"] == shop_a.id
    assert row["shop"]["name"] == "Kofi's Electronics"
    assert row["customer"]["id"] == reviewer.id
    assert row["customer"]["email"] == "ama@example.com"
    assert row["rating"] == 5
    assert "created_at" in row


def test_admin_review_list_rejects_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.get("/api/admin/reviews")

    assert response.status_code == 403
