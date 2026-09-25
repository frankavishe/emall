import pytest

from apps.accounts.models import User
from apps.feedback.models import Review
from apps.orders.models import OrderItem
from tests.factories import OrderItemFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_review_rejected_without_any_order_item(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)

    _authenticate(api_client, customer)
    response = api_client.post(
        f"/api/feedback/products/{product.id}/review", {"rating": 5}, format="json"
    )

    assert response.status_code == 403
    assert not Review.objects.filter(customer=customer, product=product).exists()


def test_review_rejected_when_order_item_not_yet_delivered(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(
        product=product, order__customer=customer, status=OrderItem.Status.PROCESSING
    )

    _authenticate(api_client, customer)
    response = api_client.post(
        f"/api/feedback/products/{product.id}/review", {"rating": 5}, format="json"
    )

    assert response.status_code == 403
    assert not Review.objects.filter(customer=customer, product=product).exists()


def test_review_rejected_for_another_customers_delivered_purchase(api_client):
    purchaser = UserFactory(role=User.Role.CUSTOMER)
    other_customer = UserFactory(role=User.Role.CUSTOMER)
    product = ProductFactory(is_published=True)
    OrderItemFactory(product=product, order__customer=purchaser)

    _authenticate(api_client, other_customer)
    response = api_client.post(
        f"/api/feedback/products/{product.id}/review", {"rating": 5}, format="json"
    )

    assert response.status_code == 403
