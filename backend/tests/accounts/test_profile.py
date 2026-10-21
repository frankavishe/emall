import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.accounts.serializers import MAX_AVATAR_SIZE_BYTES
from apps.audit.models import AuditAction, AuditEvent
from apps.core.admin_permissions import AdminRole
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def local_media(settings, tmp_path):
    """Uploads go to a temp dir, never the developer's S3/MinIO bucket."""
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    settings.MEDIA_ROOT = tmp_path


def _png(name="me.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="green").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/png")


def _put_avatar(api_client, file):
    return api_client.put("/api/auth/me/avatar", {"avatar": file}, format="multipart")


def test_me_includes_profile_fields_for_admin(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR, admin_role=AdminRole.SUPPORT_ADMIN)
    api_client.force_authenticate(admin)

    data = api_client.get("/api/auth/me").data

    assert data["phone"] == ""
    assert data["avatar_url"] is None
    assert data["date_joined"]
    assert data["admin_role"] == "SUPPORT_ADMIN"
    assert data["admin_role_label"] == "Support Admin"
    codes = {permission["code"] for permission in data["permissions"]}
    assert "orders.manage" in codes
    assert "finance.view" not in codes
    assert all(permission["label"] and permission["description"] for permission in data["permissions"])


def test_me_has_no_admin_fields_for_customer(api_client):
    api_client.force_authenticate(UserFactory())

    data = api_client.get("/api/auth/me").data

    assert data["admin_role"] is None
    assert data["admin_role_label"] is None
    assert data["permissions"] == []


def test_login_records_last_login(api_client):
    user = UserFactory()
    assert user.last_login is None

    response = api_client.post(
        "/api/auth/login",
        {"email": user.email, "password": "a-strong-password-1"},
        format="json",
    )

    user.refresh_from_db()
    assert user.last_login is not None
    assert response.data["user"]["last_login"] is not None


def test_patch_me_updates_name_and_phone_and_audits(api_client):
    user = UserFactory(name="Old Name")
    api_client.force_authenticate(user)

    response = api_client.patch(
        "/api/auth/me", {"name": "  New Name ", "phone": "+255712345678"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "New Name"
    assert response.data["phone"] == "+255712345678"
    event = AuditEvent.objects.get(action=AuditAction.ACCOUNT_PROFILE_UPDATED)
    assert event.actor == user
    assert event.metadata == {"fields": ["name", "phone"]}


def test_patch_me_without_changes_records_nothing(api_client):
    user = UserFactory(name="Same Name")
    api_client.force_authenticate(user)

    api_client.patch("/api/auth/me", {"name": "Same Name"}, format="json")

    assert not AuditEvent.objects.filter(action=AuditAction.ACCOUNT_PROFILE_UPDATED).exists()


@pytest.mark.parametrize(
    "body, field",
    [
        ({"name": ""}, "name"),
        ({"name": "A"}, "name"),
        ({"phone": "12ab"}, "phone"),
        ({"phone": "123"}, "phone"),
    ],
)
def test_patch_me_rejects_invalid_input(api_client, body, field):
    api_client.force_authenticate(UserFactory())

    response = api_client.patch("/api/auth/me", body, format="json")

    assert response.status_code == 400
    assert field in response.data


def test_patch_me_can_clear_phone(api_client):
    user = UserFactory(phone="+255712345678")
    api_client.force_authenticate(user)

    response = api_client.patch("/api/auth/me", {"phone": ""}, format="json")

    assert response.status_code == 200
    assert response.data["phone"] == ""


def test_patch_me_cannot_change_email_role_or_tier(api_client):
    admin = UserFactory(
        email="admin@example.com",
        role=User.Role.ADMINISTRATOR,
        admin_role=AdminRole.SUPPORT_ADMIN,
    )
    api_client.force_authenticate(admin)

    api_client.patch(
        "/api/auth/me",
        {"email": "other@example.com", "role": "CUSTOMER", "admin_role": "SUPER_ADMIN"},
        format="json",
    )

    admin.refresh_from_db()
    assert admin.email == "admin@example.com"
    assert admin.role == User.Role.ADMINISTRATOR
    assert admin.admin_role == AdminRole.SUPPORT_ADMIN


def test_patch_me_requires_authentication(api_client):
    assert api_client.patch("/api/auth/me", {"name": "X Y"}, format="json").status_code == 401


def test_upload_replace_and_remove_avatar(api_client):
    user = UserFactory()
    api_client.force_authenticate(user)

    first = _put_avatar(api_client, _png("first.png"))
    assert first.status_code == 200
    assert first.data["avatar_url"]
    user.refresh_from_db()
    first_name = user.avatar.name

    second = _put_avatar(api_client, _png("second.png"))
    assert second.status_code == 200
    user.refresh_from_db()
    assert user.avatar.name != first_name
    assert not user.avatar.storage.exists(first_name)
    assert user.avatar.storage.exists(user.avatar.name)

    removed = api_client.delete("/api/auth/me/avatar")
    assert removed.status_code == 200
    assert removed.data["avatar_url"] is None
    user.refresh_from_db()
    assert not user.avatar

    events = AuditEvent.objects.filter(action=AuditAction.ACCOUNT_AVATAR_UPDATED)
    assert events.count() == 3


def test_rejects_oversized_avatar(api_client):
    api_client.force_authenticate(UserFactory())
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    oversized = SimpleUploadedFile(
        "big.png", buffer.getvalue() + b"\0" * MAX_AVATAR_SIZE_BYTES, "image/png"
    )

    response = _put_avatar(api_client, oversized)

    assert response.status_code == 400
    assert "avatar" in response.data


def test_rejects_non_image_avatar(api_client):
    api_client.force_authenticate(UserFactory())
    text = SimpleUploadedFile("notes.png", b"not an image", "image/png")

    response = _put_avatar(api_client, text)

    assert response.status_code == 400
    assert "avatar" in response.data
