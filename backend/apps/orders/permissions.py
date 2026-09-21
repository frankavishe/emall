"""Object-level gating for Vendor-only actions on an OrderItem, resolved through its product's
owning Shop (research.md §5). Mirrors apps.catalog.permissions.IsProductOwner — ownership is
checked per-shop, never account-wide; the additional APPROVED-shop gate (FR-010) is applied
separately by the mutating view, mirroring IsApprovedShopOwnerForProduct's read/write asymmetry.
"""

from rest_framework.permissions import BasePermission


class IsOrderItemShopOwner(BasePermission):
    """Ownership-only check: does this order line's product belong to a shop the requester owns?
    Used for the mutating status-update action; a 404 (not 403) is returned for another vendor's
    line so no detail is leaked (FR-004)."""

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and obj.product.shop.owner_id == request.user.id
        )
