import pytest

from apps.accounts.models import User
from tests.factories import ProductFactory, RiderFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def _authenticate(api_client, user):
    response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


def test_rider_profile_reports_only_rider_role(api_client):
    rider = RiderFactory()
    _authenticate(api_client, rider)

    me = api_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.data["role"] == "RIDER"
    assert me.data["roles"] == ["RIDER"]


def test_rider_cannot_shop_or_open_a_shop(api_client):
    rider = RiderFactory()
    product = ProductFactory(is_published=True)
    _authenticate(api_client, rider)

    assert api_client.get("/api/cart").status_code == 403
    assert (
        api_client.post(
            "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
        ).status_code
        == 403
    )
    assert api_client.post("/api/checkout", {}, format="json").status_code == 403
    assert api_client.get("/api/orders").status_code == 403
    shop_response = api_client.post("/api/vendor/shops", {"name": "Sneaky"}, format="json")
    assert shop_response.status_code == 403


def test_rider_email_cannot_be_upgraded_to_vendor(api_client):
    rider = RiderFactory()
    response = api_client.post(
        "/api/auth/register/vendor",
        {"name": "x", "email": rider.email, "password": PASSWORD, "shop_name": "Rider Shop"},
        format="json",
    )
    assert response.status_code == 400
    rider.refresh_from_db()
    assert rider.is_vendor is False
    assert rider.role == User.Role.RIDER
