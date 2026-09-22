import pytest
from django.core import mail

from apps.orders.models import Order, OrderItem
from apps.orders.services import TransitionError, advance_order_item_status
from tests.factories import ProductFactory, UserFactory

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Accra",
    "region": "Greater Accra",
    "postal_code": "GA-184-9021",
    "country": "Ghana",
    "phone": "+233201234567",
}


def _make_order_item(status=OrderItem.Status.PENDING):
    product = ProductFactory(price="9.99", stock_quantity=10)
    order = Order.objects.create(customer=UserFactory(), **SHIPPING)
    return OrderItem.objects.create(
        order=order, product=product, quantity=1, unit_price=product.price, status=status
    )


@pytest.mark.django_db
def test_rejected_transition_sends_no_notification():
    order_item = _make_order_item(status=OrderItem.Status.DELIVERED)

    with pytest.raises(TransitionError):
        advance_order_item_status(order_item=order_item, new_status=OrderItem.Status.PROCESSING)

    order_item.refresh_from_db()
    assert order_item.status == OrderItem.Status.DELIVERED
    assert mail.outbox == []


@pytest.mark.django_db(transaction=True)
def test_notification_failure_does_not_block_or_roll_back_transition(monkeypatch):
    # `transaction=True` is required here (unlike the module-default `pytest.mark.django_db`):
    # `transaction.on_commit()` callbacks only fire on a real commit, which the default
    # savepoint-wrapped test transaction never performs.
    order_item = _make_order_item(status=OrderItem.Status.PENDING)

    class _RaisingEmailService:
        def send_order_item_status_email(self, order_item):
            raise RuntimeError("simulated transport failure")

    monkeypatch.setattr(
        "apps.orders.services.get_email_service", lambda: _RaisingEmailService()
    )

    result = advance_order_item_status(
        order_item=order_item, new_status=OrderItem.Status.PROCESSING
    )

    assert result.status == OrderItem.Status.PROCESSING
    order_item.refresh_from_db()
    assert order_item.status == OrderItem.Status.PROCESSING
