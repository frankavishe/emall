import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_register_customer_ignores_role_override(api_client):
    response = api_client.post(
        "/api/auth/register/customer",
        {
            "name": "Ama Owusu",
            "email": "ama-admin-attempt@example.com",
            "password": "a-strong-password-1",
            "role": "ADMINISTRATOR",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["user"]["role"] == "CUSTOMER"
    user = User.objects.get(email="ama-admin-attempt@example.com")
    assert user.role == User.Role.CUSTOMER


def test_register_vendor_ignores_role_override(api_client):
    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Kofi Mensah",
            "email": "kofi-admin-attempt@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Kofi's Admin Attempt Shop",
            "role": "ADMINISTRATOR",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["user"]["role"] == "VENDOR"
    user = User.objects.get(email="kofi-admin-attempt@example.com")
    assert user.role == User.Role.VENDOR


def test_no_public_endpoint_creates_administrator(api_client):
    api_client.post(
        "/api/auth/register/customer",
        {
            "name": "Someone",
            "email": "someone@example.com",
            "password": "a-strong-password-1",
            "role": "ADMINISTRATOR",
        },
        format="json",
    )
    api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Someone Else",
            "email": "someone-else@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Someone Else's Shop",
            "role": "ADMINISTRATOR",
        },
        format="json",
    )

    assert not User.objects.filter(role=User.Role.ADMINISTRATOR).exists()
