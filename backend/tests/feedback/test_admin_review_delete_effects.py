import pytest

from apps.accounts.models import User
from apps.orders.models import OrderItem
from apps.vendors.models import Shop
from tests.factories import (
    OrderItemFactory,
    ProductFactory,
    ReviewFactory,
    ShopFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_deleted_review_disappears_from_catalog_vendor_view_and_can_be_resubmitted(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True)
    customer = UserFactory(role=User.Role.CUSTOMER)
    OrderItemFactory(
        product=product, order__customer=customer, status=OrderItem.Status.DELIVERED
    )
    review = ReviewFactory(customer=customer, product=product, rating=1, comment="Not great.")

    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    _authenticate(api_client, admin)
    delete_response = api_client.delete(f"/api/admin/reviews/{review.id}")
    assert delete_response.status_code == 204

    api_client.credentials()
    catalog_response = api_client.get(f"/api/catalog/products/{product.id}")
    assert catalog_response.data["average_rating"] is None
    assert catalog_response.data["review_count"] == 0
    assert catalog_response.data["reviews"] == []

    _authenticate(api_client, vendor)
    vendor_response = api_client.get("/api/vendor/reviews")
    assert vendor_response.data["count"] == 0

    _authenticate(api_client, customer)
    resubmit_response = api_client.post(
        f"/api/feedback/products/{product.id}/review",
        {"rating": 4, "comment": "Changed my mind, works fine."},
        format="json",
    )
    assert resubmit_response.status_code == 201
    assert resubmit_response.data["id"] != review.id
    assert resubmit_response.data["rating"] == 4
