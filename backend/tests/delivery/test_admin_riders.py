import pytest

from apps.accounts.models import User
from apps.delivery.models import RiderProfile
from tests.factories import RiderFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"

NEW_RIDER = {
    "name": "Juma Rider",
    "email": "Juma@Example.com",
    "password": "temp-pass-4567",
    "phone": "+255711111111",
    "vehicle_type": "MOTORCYCLE",
    "plate_number": "MC 999 XYZ",
}


def _login(api_client, email, password=PASSWORD):
    return api_client.post("/api/auth/login", {"email": email, "password": password}, format="json")


def _authenticate(api_client, user, password=PASSWORD):
    response = _login(api_client, user.email, password)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


@pytest.fixture
def admin(api_client):
    user = UserFactory(role=User.Role.ADMINISTRATOR, is_email_verified=True)
    _authenticate(api_client, user)
    return user


def test_admin_registers_rider_who_can_then_log_in(api_client, admin):
    response = api_client.post("/api/admin/riders", NEW_RIDER, format="json")

    assert response.status_code == 201
    assert response.data["email"] == "juma@example.com"
    assert response.data["phone"] == "+255711111111"
    assert response.data["vehicle_type"] == "MOTORCYCLE"
    assert response.data["plate_number"] == "MC 999 XYZ"
    assert response.data["is_active"] is True
    assert response.data["active_delivery_count"] == 0
    assert "password" not in response.data

    rider = User.objects.get(email="juma@example.com")
    assert rider.role == User.Role.RIDER
    assert rider.is_email_verified is True
    assert RiderProfile.objects.filter(user=rider).exists()

    api_client.credentials()
    login = _login(api_client, "juma@example.com", "temp-pass-4567")
    assert login.status_code == 200
    assert login.data["user"]["roles"] == ["RIDER"]


def test_duplicate_email_rejected(api_client, admin):
    UserFactory(email="juma@example.com")
    response = api_client.post("/api/admin/riders", NEW_RIDER, format="json")
    assert response.status_code == 400
    assert "email" in response.data


def test_weak_password_rejected(api_client, admin):
    response = api_client.post(
        "/api/admin/riders", {**NEW_RIDER, "password": "123"}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.data
    assert not User.objects.filter(email="juma@example.com").exists()


@pytest.mark.parametrize("role", [User.Role.CUSTOMER, User.Role.RIDER])
def test_non_admin_cannot_manage_riders(api_client, role):
    user = RiderFactory() if role == User.Role.RIDER else UserFactory(role=role)
    _authenticate(api_client, user)

    assert api_client.get("/api/admin/riders").status_code == 403
    assert api_client.post("/api/admin/riders", NEW_RIDER, format="json").status_code == 403


def test_anonymous_cannot_manage_riders(api_client):
    assert api_client.get("/api/admin/riders").status_code == 401


def test_admin_lists_riders_with_active_filter(api_client, admin):
    active = RiderFactory(name="Active Rider")
    inactive = RiderFactory(name="Inactive Rider", is_active=False)
    UserFactory(role=User.Role.CUSTOMER)

    all_ids = {r["id"] for r in api_client.get("/api/admin/riders").data["results"]}
    assert all_ids == {active.id, inactive.id}

    active_ids = {
        r["id"] for r in api_client.get("/api/admin/riders?is_active=true").data["results"]
    }
    assert active_ids == {active.id}


def test_admin_updates_rider_details(api_client, admin):
    rider = RiderFactory()
    response = api_client.patch(
        f"/api/admin/riders/{rider.id}",
        {"phone": "+255722222222", "vehicle_type": "VAN", "name": "New Name"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["phone"] == "+255722222222"
    assert response.data["vehicle_type"] == "VAN"
    assert response.data["name"] == "New Name"


def test_patch_on_non_rider_404s(api_client, admin):
    customer = UserFactory(role=User.Role.CUSTOMER)
    response = api_client.patch(
        f"/api/admin/riders/{customer.id}", {"is_active": False}, format="json"
    )
    assert response.status_code == 404
    customer.refresh_from_db()
    assert customer.is_active is True


def test_deactivated_rider_cannot_log_in_and_is_logged_out(api_client):
    rider = RiderFactory()
    rider_client = type(api_client)()
    login = _login(rider_client, rider.email)
    assert login.status_code == 200

    admin = UserFactory(role=User.Role.ADMINISTRATOR, is_email_verified=True)
    _authenticate(api_client, admin)
    response = api_client.patch(
        f"/api/admin/riders/{rider.id}", {"is_active": False}, format="json"
    )
    assert response.status_code == 200
    assert response.data["is_active"] is False

    # Their existing session's refresh token no longer works...
    assert rider_client.post("/api/auth/refresh").status_code == 401
    # ...and they can't log in again.
    assert _login(type(api_client)(), rider.email).status_code == 401

    # Reactivating lets them back in.
    api_client.patch(f"/api/admin/riders/{rider.id}", {"is_active": True}, format="json")
    assert _login(type(api_client)(), rider.email).status_code == 200


def test_admin_resets_rider_password(api_client, admin):
    rider = RiderFactory()
    response = api_client.patch(
        f"/api/admin/riders/{rider.id}", {"password": "brand-new-pass-99"}, format="json"
    )
    assert response.status_code == 200

    assert _login(type(api_client)(), rider.email).status_code == 401
    assert _login(type(api_client)(), rider.email, "brand-new-pass-99").status_code == 200
