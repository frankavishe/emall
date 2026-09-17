"""Object-level gating for Vendor-only actions on a Product, resolved through its owning Shop
(research.md §5). Mirrors apps.vendors.permissions.IsApprovedShopOwner — approval status and
ownership are checked per-shop, never account-wide.
"""

from rest_framework.permissions import BasePermission

from apps.vendors.models import Shop


class IsApprovedShopOwnerForProduct(BasePermission):
    """Use for create and publish — FR-002/FR-004 require the shop to be APPROVED, not just
    owned by the requester."""

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and obj.shop.status == Shop.Status.APPROVED
            and obj.shop.owner_id == request.user.id
        )


class IsProductOwner(BasePermission):
    """Ownership-only check for actions that don't require the shop to currently be APPROVED —
    edit, delete, unpublish, list (FR-003/FR-005/FR-006/FR-014). A shop that is no longer
    APPROVED shouldn't strand a Vendor's ability to manage/unpublish/delete their own products."""

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and obj.shop.owner_id == request.user.id
        )
