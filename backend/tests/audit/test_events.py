import json
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditEvent
from apps.finance.models import PlatformSettings
from apps.orders.models import OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from tests.factories import OrderItemFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


def _event(action):
    return AuditEvent.objects.get(action=action)


def test_login_and_failed_login(api_client):
    user = UserFactory(email="shopper@example.com")

    api_client.post("/api/auth/login", {"email": user.email, "password": PASSWORD}, format="json")
    api_client.post("/api/auth/login", {"email": user.email, "password": "wrong"}, format="json")

    login = _event(AuditAction.LOGIN)
    assert login.actor == user
    assert login.target_id == str(user.id)
    failed = _event(AuditAction.LOGIN_FAILED)
    assert failed.actor is None
    assert failed.target_id == str(user.id)
    assert failed.metadata == {"email": "shopper@example.com", "reason": "invalid"}


def test_shop_approve_and_reject(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    approved = ShopFactory(status=Shop.Status.PENDING)
    rejected = ShopFactory(status=Shop.Status.PENDING)
    api_client.force_authenticate(admin)

    api_client.post(f"/api/admin/shops/{approved.id}/approve")
    api_client.post(f"/api/admin/shops/{rejected.id}/reject", {"reason": "Blurry ID"})

    assert _event(AuditAction.SHOP_APPROVED).target_id == str(approved.id)
    reject = _event(AuditAction.SHOP_REJECTED)
    assert reject.actor == admin
    assert reject.metadata == {"reason": "Blurry ID"}


def test_customer_block(api_client):
    customer = UserFactory()
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))

    api_client.patch(f"/api/admin/customers/{customer.id}", {"is_active": False}, format="json")

    assert _event(AuditAction.CUSTOMER_BLOCKED).target_repr == customer.email


def test_settings_update_records_before_and_after(api_client):
    platform = PlatformSettings.get_solo()
    platform.default_commission_rate = Decimal("10.00")
    platform.save()
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))

    api_client.patch(
        "/api/admin/finance/settings", {"default_commission_rate": "25"}, format="json"
    )

    changes = _event(AuditAction.SETTINGS_UPDATED).metadata["changes"]
    assert changes == {"default_commission_rate": {"from": "10.00", "to": "25.00"}}


def test_vendor_publishes_product(api_client):
    product = ProductFactory()
    api_client.force_authenticate(product.shop.owner)

    response = api_client.post(f"/api/vendor/products/{product.id}/publish")

    assert response.status_code == 200
    event = _event(AuditAction.PRODUCT_PUBLISHED)
    assert event.actor_role == "VENDOR"
    assert event.target_repr == product.name


def test_vendor_order_item_status_change(api_client):
    item = OrderItemFactory(status=OrderItem.Status.PROCESSING)
    api_client.force_authenticate(item.product.shop.owner)

    api_client.patch(
        f"/api/vendor/order-items/{item.id}/status", {"status": "SHIPPED"}, format="json"
    )

    event = _event(AuditAction.ORDER_ITEM_STATUS_CHANGED)
    assert event.metadata == {"from": "PROCESSING", "to": "SHIPPED"}
    assert event.target_repr == f"Order #{item.order_id} · {item.product.name}"


def test_manual_payment_settle(api_client):
    item = OrderItemFactory(status=OrderItem.Status.PENDING)
    PaymentRecord.objects.create(
        order=item.order,
        method="cod",
        amount="9.99",
        transaction_reference="ref-cod",
        status=PaymentRecord.Status.PENDING,
    )
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    api_client.force_authenticate(admin)

    response = api_client.post(f"/api/admin/orders/{item.order_id}/payment/confirm")

    assert response.status_code == 200
    event = _event(AuditAction.PAYMENT_CONFIRMED)
    assert event.actor == admin
    assert event.target_id == str(item.order_id)
    # The admin's settlement is not double-counted as a system payment event.
    assert not AuditEvent.objects.filter(action=AuditAction.PAYMENT_COMPLETED).exists()


def test_metadata_never_holds_secrets(api_client):
    user = UserFactory()
    api_client.post("/api/auth/login", {"email": user.email, "password": PASSWORD}, format="json")
    api_client.post("/api/auth/login", {"email": user.email, "password": "nope"}, format="json")

    for event in AuditEvent.objects.all():
        dumped = json.dumps(event.metadata).lower()
        assert "password" not in dumped
        assert PASSWORD not in dumped
        assert "token" not in dumped
