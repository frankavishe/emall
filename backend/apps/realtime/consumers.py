"""The realtime socket at `/ws/`.

The client speaks JSON:
- `{"type": "auth", "token": "<access JWT>"}`: a signed-in user, who then hears about their own
  orders and, as a vendor or rider, their own lines; an administrator about every order. The
  token travels in a message, not the URL, so it never lands in proxy logs; the refresh cookie
  can't help (it is scoped to /api/auth/).
- `{"type": "subscribe", "order_id": N}`: one order by id (a customer's own; an administrator's
  any). Signed-in buyers already hear about their orders, so this is mostly for admins.
- `{"type": "subscribe", "guest_token": "..."}`: a guest watching the order behind that token.
- `{"type": "unsubscribe", ...}`: the same shapes, to stop.

The server only ever sends hints (see broadcast.py) and replies to the messages above.
"""

import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.orders.models import Order
from apps.realtime.groups import ADMINS, order_group, user_group

# A socket that hasn't authenticated or subscribed by then is dropped.
IDLE_TIMEOUT_SECONDS = 10
# Nobody legitimately watches more orders than this on one socket.
MAX_ORDER_SUBSCRIPTIONS = 50


@database_sync_to_async
def _user_for_token(token):
    try:
        user_id = AccessToken(token)["user_id"]
    except (TokenError, KeyError):
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


@database_sync_to_async
def _order_id_for(user, order_id=None, guest_token=None):
    """The order id the requester may watch, or None. Mirrors the REST views: a customer reaches
    their own orders, an administrator who may view orders any order, a guest only the order
    behind its token."""

    if guest_token:
        return (
            Order.objects.filter(access_token=str(guest_token))
            .values_list("id", flat=True)
            .first()
        )
    if user is None or not isinstance(order_id, int):
        return None
    orders = Order.objects.filter(pk=order_id)
    if not user.has_admin_permission("orders.view"):
        orders = orders.filter(customer=user)
    return orders.values_list("id", flat=True).first()


def _account_groups(user):
    groups = [user_group(user.id)]
    if user.has_role(User.Role.ADMINISTRATOR):
        groups.append(ADMINS)
    return groups


class RealtimeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = None
        self.groups_joined = set()
        await self.accept()
        self.idle_timer = asyncio.create_task(self._close_if_idle())

    async def disconnect(self, code):
        if getattr(self, "idle_timer", None) is not None:
            self.idle_timer.cancel()
        for group in self.groups_joined:
            await self.channel_layer.group_discard(group, self.channel_name)
        self.groups_joined.clear()

    async def _close_if_idle(self):
        await asyncio.sleep(IDLE_TIMEOUT_SECONDS)
        if self.user is None and not self.groups_joined:
            await self.close(code=4401)

    async def _join(self, group):
        if group not in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)
            self.groups_joined.add(group)

    async def _leave(self, group):
        if group in self.groups_joined:
            await self.channel_layer.group_discard(group, self.channel_name)
            self.groups_joined.discard(group)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            return
        kind = content.get("type")
        if kind == "auth":
            await self._auth(content.get("token"))
        elif kind in ("subscribe", "unsubscribe"):
            await self._subscription(kind, content)

    async def _auth(self, token):
        user = await _user_for_token(token) if isinstance(token, str) else None
        if user is None:
            await self.send_json({"type": "auth.error"})
            return
        if self.user is not None and self.user.id != user.id:
            # A different account on the same socket: start over rather than mix audiences.
            await self.close(code=4409)
            return
        self.user = user
        for group in _account_groups(user):
            await self._join(group)
        await self.send_json({"type": "auth.ok"})

    async def _subscription(self, kind, content):
        order_id = await _order_id_for(
            self.user, order_id=content.get("order_id"), guest_token=content.get("guest_token")
        )
        reply = {key: content[key] for key in ("order_id", "guest_token") if key in content}
        if order_id is None:
            await self.send_json({"type": f"{kind}.error", **reply})
            return
        group = order_group(order_id)
        if kind == "unsubscribe":
            await self._leave(group)
        else:
            orders_watched = sum(1 for g in self.groups_joined if g.startswith("order."))
            if group not in self.groups_joined and orders_watched >= MAX_ORDER_SUBSCRIPTIONS:
                await self.send_json({"type": "subscribe.error", **reply})
                return
            await self._join(group)
        await self.send_json({"type": f"{kind}d", **reply})

    async def realtime_event(self, event):
        await self.send_json(event["payload"])
