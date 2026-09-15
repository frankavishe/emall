"""Object-level gating for Vendor-only actions on a specific Shop (research.md §5).

Approval status and ownership are checked per-shop, never account-wide — a Vendor with one
APPROVED shop and one PENDING shop may act on the former but not the latter.
"""

from rest_framework.permissions import BasePermission

from apps.vendors.models import Shop


class IsApprovedShopOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and obj.status == Shop.Status.APPROVED
            and obj.owner_id == request.user.id
        )
