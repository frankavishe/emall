from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.audit.services import record
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

URL = "/api/admin/audit-events"


@pytest.mark.parametrize("role", [User.Role.CUSTOMER, User.Role.VENDOR, User.Role.RIDER])
def test_only_administrators_can_read(api_client, role):
    api_client.force_authenticate(UserFactory(role=role))
    assert api_client.get(URL).status_code == 403


def test_anonymous_cannot_read(api_client):
    assert api_client.get(URL).status_code == 401


def test_filters(api_client):
    alice = UserFactory(email="alice@example.com")
    bob = UserFactory(email="bob@example.com", role=User.Role.ADMINISTRATOR)
    record(AuditAction.LOGIN, actor=alice, target=alice)
    record(AuditAction.SHOP_APPROVED, actor=bob, target_type="shop", target_id=5)
    record(AuditAction.SHOP_REJECTED, actor=bob, target_type="shop", target_id=6)
    old = record(AuditAction.PAYMENT_EXPIRED, target_type="order", target_id=1)
    AuditEvent.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=10))
    api_client.force_authenticate(bob)

    def actions(**params):
        results = api_client.get(URL, params).data["results"]
        return sorted(row["action"] for row in results)

    assert actions(action="shop.") == ["shop.approved", "shop.rejected"]
    assert actions(action="shop.approved") == ["shop.approved"]
    assert actions(actor="alice") == ["auth.login"]
    assert actions(actor_role="SYSTEM") == ["payment.expired"]
    assert actions(target_type="shop", target_id="6") == ["shop.rejected"]
    week_ago = (timezone.now() - timedelta(days=7)).date().isoformat()
    assert "payment.expired" not in actions(**{"from": week_ago})
    assert actions(to=week_ago) == ["payment.expired"]
    assert api_client.get(URL, {"from": "not-a-date"}).status_code == 400


def test_newest_first_and_paginated(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    for _ in range(3):
        record(AuditAction.LOGIN, actor=admin)
    api_client.force_authenticate(admin)

    data = api_client.get(URL, {"page_size": 2}).data

    assert data["count"] == 3
    assert len(data["results"]) == 2
    assert data["results"][0]["id"] > data["results"][1]["id"]
    assert data["results"][0]["action_label"] == "Signed in"
