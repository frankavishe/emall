from unittest import mock

import pytest
from django.db import transaction
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.audit.services import client_ip, record
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _request(path="/api/admin/x", **meta):
    request = APIRequestFactory().post(path, **meta)
    request.user = UserFactory(role=User.Role.ADMINISTRATOR)
    return request


def test_actor_target_and_client_details_come_from_the_request():
    request = _request(HTTP_USER_AGENT="Browser/1.0", REMOTE_ADDR="10.0.0.9")
    shop = ShopFactory(name="Mama Shop")

    event = record(AuditAction.SHOP_APPROVED, request=request, target=shop)

    assert event.actor == request.user
    assert event.actor_email == request.user.email
    assert event.actor_role == "ADMINISTRATOR"
    assert (event.target_type, event.target_id, event.target_repr) == (
        "shop",
        str(shop.id),
        "Mama Shop",
    )
    assert event.ip_address == "10.0.0.9"
    assert event.user_agent == "Browser/1.0"


def test_ip_is_the_proxy_appended_forwarded_entry():
    request = _request(HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.7", REMOTE_ADDR="172.18.0.2")
    assert client_ip(request) == "203.0.113.7"


def test_vendor_api_records_vendor_role():
    vendor = UserFactory(role=User.Role.VENDOR)
    request = APIRequestFactory().patch("/api/vendor/shops/1/theme")
    request.user = vendor

    event = record(AuditAction.SHOP_PROFILE_UPDATED, request=request, target=vendor)

    assert event.actor_role == "VENDOR"


def test_system_event_has_no_actor():
    event = record(AuditAction.PAYMENT_EXPIRED, target_type="order", target_id=7)

    assert event.actor is None
    assert event.actor_role == AuditEvent.SYSTEM_ROLE
    assert event.target_id == "7"


def test_failed_write_never_breaks_the_caller():
    with mock.patch.object(AuditEvent.objects, "create", side_effect=RuntimeError("db down")):
        assert record(AuditAction.LOGIN, request=_request()) is None


def test_rolled_back_action_leaves_no_row():
    request = _request()
    with pytest.raises(ValueError), transaction.atomic():
        record(AuditAction.LOGIN, request=request)
        raise ValueError

    assert not AuditEvent.objects.exists()
