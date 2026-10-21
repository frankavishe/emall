import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.core.admin_permissions import ROLE_PERMISSIONS, AdminPermission, AdminRole
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

# One request per admin area: (method, url, the permission it needs).
READS = [
    ("get", "/api/admin/shops", "shops.view"),
    ("get", "/api/admin/products", "catalog.view"),
    ("get", "/api/admin/categories", "catalog.view"),
    ("get", "/api/admin/customers", "customers.view"),
    ("get", "/api/admin/order-items", "orders.view"),
    ("get", "/api/admin/riders", "riders.view"),
    ("get", "/api/admin/finance/summary", "finance.view"),
    ("get", "/api/admin/payouts", "finance.view"),
    ("get", "/api/admin/transactions", "finance.view"),
    ("get", "/api/admin/reviews", "reviews.view"),
    ("get", "/api/admin/audit-events", "audit.view"),
]
WRITES = [
    ("post", "/api/admin/categories", "catalog.manage"),
    ("patch", "/api/admin/finance/settings", "finance.manage"),
    ("post", "/api/admin/riders", "riders.manage"),
    ("post", "/api/admin/orders/999999/payment/confirm", "finance.manage"),
    ("post", "/api/admin/shops/999999/approve", "shops.manage"),
    ("post", "/api/admin/order-items/999999/rider", "orders.manage"),
]


def _admin(admin_role):
    return UserFactory(role=User.Role.ADMINISTRATOR, admin_role=admin_role)


def _call(api_client, method, url):
    return getattr(api_client, method)(url, {}, format="json")


@pytest.mark.parametrize("method, url, needs", READS + WRITES)
def test_support_admin_is_limited_to_its_permissions(api_client, method, url, needs):
    api_client.force_authenticate(_admin(AdminRole.SUPPORT_ADMIN))

    response = _call(api_client, method, url)

    allowed = needs in ROLE_PERMISSIONS[AdminRole.SUPPORT_ADMIN]
    if allowed:
        assert response.status_code != 403
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("method, url, needs", READS + WRITES)
def test_super_admin_reaches_every_area(api_client, method, url, needs):
    api_client.force_authenticate(_admin(AdminRole.SUPER_ADMIN))

    assert _call(api_client, method, url).status_code != 403


@pytest.mark.parametrize("method, url, needs", READS)
def test_admin_without_tier_is_denied(api_client, method, url, needs):
    api_client.force_authenticate(_admin(None))

    assert _call(api_client, method, url).status_code == 403


@pytest.mark.parametrize("method, url, needs", READS)
def test_non_admin_is_denied(api_client, method, url, needs):
    api_client.force_authenticate(UserFactory())

    assert _call(api_client, method, url).status_code == 403


def test_support_admin_cannot_do_finance_or_audit():
    granted = ROLE_PERMISSIONS[AdminRole.SUPPORT_ADMIN]
    assert not any(p.startswith(("finance.", "audit.")) for p in granted)


def test_super_admin_has_every_permission():
    assert ROLE_PERMISSIONS[AdminRole.SUPER_ADMIN] == frozenset(AdminPermission)


def test_set_admin_role_command_changes_tier_and_audits():
    admin = _admin(AdminRole.SUPER_ADMIN)

    call_command("set_admin_role", admin.email.upper(), "SUPPORT_ADMIN")

    admin.refresh_from_db()
    assert admin.admin_role == AdminRole.SUPPORT_ADMIN
    event = AuditEvent.objects.get(action=AuditAction.ADMIN_ROLE_CHANGED)
    assert event.metadata == {"from": "SUPER_ADMIN", "to": "SUPPORT_ADMIN"}


def test_set_admin_role_command_refuses_non_admins():
    customer = UserFactory()

    with pytest.raises(CommandError):
        call_command("set_admin_role", customer.email, "SUPER_ADMIN")


def test_createsuperuser_defaults_to_super_admin():
    user = User.objects.create_superuser("root@example.com", "a-strong-password-1", name="Root")

    assert user.admin_role == AdminRole.SUPER_ADMIN
