import pytest

from apps.accounts.models import User
from tests.factories import OrderItemFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_customer_submits_review_with_rating_and_comment(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(product=product, order__customer=customer)

    _authenticate(api_client, customer)
    response = api_client.post(
        f"/api/feedback/products/{product.id}/review",
        {"rating": 5, "comment": "Works great, fast shipping."},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["rating"] == 5
    assert response.data["comment"] == "Works great, fast shipping."
    assert response.data["product"] == product.id


def test_customer_submits_review_with_rating_only(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(product=product, order__customer=customer)

    _authenticate(api_client, customer)
    response = api_client.post(
        f"/api/feedback/products/{product.id}/review", {"rating": 3}, format="json"
    )

    assert response.status_code == 201
    assert response.data["rating"] == 3
    assert response.data["comment"] == ""
