import pytest

from apps.accounts.models import User
from apps.feedback.models import Review
from tests.factories import OrderItemFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_repeat_submission_updates_existing_review_not_a_new_one(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(product=product, order__customer=customer)

    _authenticate(api_client, customer)
    first = api_client.post(
        f"/api/feedback/products/{product.id}/review",
        {"rating": 5, "comment": "Works great."},
        format="json",
    )
    second = api_client.post(
        f"/api/feedback/products/{product.id}/review",
        {"rating": 3, "comment": "Actually just okay."},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.data["id"] == first.data["id"]
    assert second.data["rating"] == 3
    assert second.data["comment"] == "Actually just okay."
    assert Review.objects.filter(customer=customer, product=product).count() == 1
