"""The `/ws/` socket: who may listen to what, end to end through the in-memory channel layer."""

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.orders.models import OrderItem
from apps.orders.services import advance_order_item_status
from apps.realtime import consumers
from config.asgi import application
from tests.factories import OrderFactory, OrderItemFactory, RiderFactory, UserFactory

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]

# The first CORS origin is trusted (config.asgi reads the list once, at import).
ORIGIN = (b"origin", settings.CORS_ALLOWED_ORIGINS[0].encode())
# Generous: the first database call on a fresh thread pool can take over a second.
TIMEOUT = 5


def _token(user):
    return str(AccessToken.for_user(user))


async def _connect(origin=ORIGIN):
    communicator = WebsocketCommunicator(application, "/ws/", headers=[origin])
    connected, _ = await communicator.connect()
    assert connected
    return communicator


async def _send(communicator, message):
    await communicator.send_json_to(message)
    return await communicator.receive_json_from(timeout=TIMEOUT)


@pytest.fixture
def item():
    return OrderItemFactory(status=OrderItem.Status.PENDING)


async def test_foreign_origin_is_refused():
    communicator = WebsocketCommunicator(
        application, "/ws/", headers=[(b"origin", b"https://evil.example")]
    )
    connected, _ = await communicator.connect()
    assert not connected


async def test_bad_token_is_rejected():
    communicator = await _connect()
    assert await _send(communicator, {"type": "auth", "token": "nope"}) == {"type": "auth.error"}
    await communicator.disconnect()


async def test_idle_socket_is_closed(monkeypatch):
    monkeypatch.setattr(consumers, "IDLE_TIMEOUT_SECONDS", 0.05)
    communicator = await _connect()
    output = await communicator.receive_output(timeout=TIMEOUT)
    assert output["type"] == "websocket.close"


async def test_customer_hears_about_own_order(item):
    communicator = await _connect()
    assert (await _send(communicator, {"type": "auth", "token": _token(item.order.customer)}))[
        "type"
    ] == "auth.ok"
    reply = await _send(communicator, {"type": "subscribe", "order_id": item.order_id})
    assert reply == {"type": "subscribed", "order_id": item.order_id}

    await database_sync_to_async(advance_order_item_status)(
        order_item=item, new_status=OrderItem.Status.PROCESSING
    )

    assert await communicator.receive_json_from(timeout=TIMEOUT) == {
        "type": "order.updated",
        "order_id": item.order_id,
    }
    await communicator.disconnect()


async def test_signed_in_customer_hears_without_subscribing(item):
    communicator = await _connect()
    await _send(communicator, {"type": "auth", "token": _token(item.order.customer)})

    await database_sync_to_async(advance_order_item_status)(
        order_item=item, new_status=OrderItem.Status.PROCESSING
    )

    assert (await communicator.receive_json_from(timeout=TIMEOUT))["type"] == "order.updated"
    await communicator.disconnect()


async def test_customer_cannot_watch_someone_elses_order(item):
    stranger = await database_sync_to_async(UserFactory)()
    communicator = await _connect()
    await _send(communicator, {"type": "auth", "token": _token(stranger)})
    reply = await _send(communicator, {"type": "subscribe", "order_id": item.order_id})
    assert reply["type"] == "subscribe.error"
    await communicator.disconnect()


async def test_anonymous_cannot_watch_by_order_id(item):
    communicator = await _connect()
    reply = await _send(communicator, {"type": "subscribe", "order_id": item.order_id})
    assert reply["type"] == "subscribe.error"
    await communicator.disconnect()


async def test_guest_watches_by_token():
    order = await database_sync_to_async(OrderFactory)(
        customer=None, guest_email="ama@example.com", access_token="guest-secret"
    )
    item = await database_sync_to_async(OrderItemFactory)(
        order=order, status=OrderItem.Status.PENDING
    )
    communicator = await _connect()
    reply = await _send(communicator, {"type": "subscribe", "guest_token": "guest-secret"})
    assert reply["type"] == "subscribed"
    assert (await _send(communicator, {"type": "subscribe", "guest_token": "wrong"}))[
        "type"
    ] == "subscribe.error"

    await database_sync_to_async(advance_order_item_status)(
        order_item=item, new_status=OrderItem.Status.PROCESSING
    )
    assert (await communicator.receive_json_from(timeout=TIMEOUT))["type"] == "order.updated"
    await communicator.disconnect()


async def test_vendor_rider_and_admin_join_their_own_groups(item):
    rider = await database_sync_to_async(RiderFactory)()
    item.rider = rider
    await database_sync_to_async(item.save)()
    admin = await database_sync_to_async(UserFactory)(role=User.Role.ADMINISTRATOR)
    vendor = await database_sync_to_async(lambda: item.product.shop.owner)()
    bystander_vendor = await database_sync_to_async(UserFactory)(role=User.Role.VENDOR)

    sockets = {}
    for name, user in [
        ("vendor", vendor),
        ("rider", rider),
        ("admin", admin),
        ("bystander", bystander_vendor),
    ]:
        sockets[name] = await _connect()
        assert (await _send(sockets[name], {"type": "auth", "token": _token(user)}))[
            "type"
        ] == "auth.ok"

    await database_sync_to_async(advance_order_item_status)(
        order_item=item, new_status=OrderItem.Status.PROCESSING
    )

    for name in ("vendor", "rider", "admin"):
        event = await sockets[name].receive_json_from(timeout=TIMEOUT)
        assert event == {"type": "order.updated", "order_id": item.order_id}, name
    assert await sockets["bystander"].receive_nothing()

    for communicator in sockets.values():
        await communicator.disconnect()
