import pytest

from apps.accounts.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_get_cart_creates_it_lazily_and_returns_empty_shape(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, customer)

    response = api_client.get("/api/cart")

    assert response.status_code == 200
    assert response.data["items"] == []
    assert response.data["total"] == "0.00"


def test_get_cart_requires_customer_role(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    _authenticate(api_client, vendor)

    response = api_client.get("/api/cart")

    assert response.status_code == 403
