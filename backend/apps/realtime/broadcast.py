"""Telling open sockets that something changed. A message is only a hint, such as
`{"type": "order.updated", "order_id": 42}`, and never carries order data: the page refetches
through the REST API, which keeps every permission check where it already is.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def publish(groups, event):
    """Best-effort, like the status emails: a broadcast problem must never look like a failure
    of the (already-committed) change it announces."""

    try:
        layer = get_channel_layer()
        if layer is None:
            return
        send = async_to_sync(layer.group_send)
        for group in dict.fromkeys(groups):
            send(group, {"type": "realtime.event", "payload": event})
    except Exception:
        logger.exception("Failed to publish realtime event %s", event)


def publish_on_commit(groups, event):
    """Publishes once the surrounding transaction commits (immediately outside one), so a
    rolled-back change is never announced."""

    groups = list(groups)
    transaction.on_commit(lambda: publish(groups, event))
