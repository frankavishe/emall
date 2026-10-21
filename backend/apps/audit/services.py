"""Writing the audit trail. Call `record()` from the view right after a mutation succeeds (the
view holds the request, so actor, IP and user agent come for free); system events with no
request pass `actor=None`."""

import logging
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import transaction

from apps.audit.models import AuditAction, AuditEvent

logger = logging.getLogger(__name__)

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def record(
    action,
    *,
    request=None,
    actor=None,
    actor_role=None,
    target=None,
    target_type=None,
    target_id=None,
    target_repr=None,
    metadata=None,
):
    """Append one AuditEvent. Runs in a savepoint inside the caller's transaction, so a rolled-back
    action leaves no row, while a failed audit write is logged and never breaks the action."""

    if actor is None and request is not None:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            actor = user
    if target is not None:
        target_type = target_type or _CAMEL_BOUNDARY.sub("_", type(target).__name__).lower()
        target_id = target_id if target_id is not None else target.pk
        target_repr = target_repr if target_repr is not None else str(target)
    try:
        with transaction.atomic():
            return AuditEvent.objects.create(
                action=AuditAction(action),
                actor=actor,
                actor_email=actor.email if actor else "",
                actor_role=actor_role or _actor_role(actor, request),
                target_type=target_type or "",
                target_id="" if target_id is None else str(target_id),
                target_repr=(target_repr or "")[:255],
                metadata=metadata or {},
                ip_address=client_ip(request),
                user_agent=_user_agent(request),
            )
    except Exception:
        logger.exception("Failed to record audit event %s", action)
        return None


def changed_fields(instance, data, fields=None):
    """Names of the fields in `data` whose value differs from `instance`'s (call before saving)."""

    return sorted(
        name
        for name, value in data.items()
        if (fields is None or name in fields) and getattr(instance, name, None) != value
    )


def client_ip(request):
    if request is None:
        return None
    # Production sits behind exactly one proxy (Caddy). Its entry is the last one in
    # X-Forwarded-For; anything before it came from the client and can be forged.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[-1].strip() or request.META.get("REMOTE_ADDR") or None
    return ip if ip and _looks_like_ip(ip) else None


def _looks_like_ip(value):
    try:
        validate_ipv46_address(value)
    except ValidationError:
        return False
    return True


def _user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def _actor_role(actor, request):
    if actor is None:
        return AuditEvent.SYSTEM_ROLE if request is None else ""
    # One account can be both customer and vendor; the vendor API is the vendor acting.
    if (
        actor.has_role("VENDOR")
        and request is not None
        and request.path.startswith("/api/vendor/")
    ):
        return "VENDOR"
    return actor.role


def order_item_repr(order_item):
    return f"Order #{order_item.order_id} · {order_item.product.name}"[:255]
