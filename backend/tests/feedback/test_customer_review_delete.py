import pytest

from apps.accounts.models import User
from apps.feedback.models import Review
from tests.factories import OrderItemFactory, ProductFactory, ReviewFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_customer_deletes_their_own_review(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(product=product, order__customer=customer)
    ReviewFactory(customer=customer, product=product)

    _authenticate(api_client, customer)
    response = api_client.delete(f"/api/feedback/products/{product.id}/review")

    assert response.status_code == 204
    assert not Review.objects.filter(customer=customer, product=product).exists()


def test_deleting_already_deleted_review_returns_404(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)

    _authenticate(api_client, customer)
    first = api_client.delete(f"/api/feedback/products/{product.id}/review")
    second = api_client.delete(f"/api/feedback/products/{product.id}/review")

    assert first.status_code == 404
    assert second.status_code == 404
