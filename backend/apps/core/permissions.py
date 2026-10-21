"""Server-side role checks (Constitution Principle I: enforced on every request; client-side role
checks MUST NOT be relied upon for authorization).
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission


def require_verified_email(user):
    if not user.is_email_verified:
        raise PermissionDenied("This action requires a verified email address.")


def IsRole(role):
    class _IsRole(BasePermission):
        def has_permission(self, request, view):
            return bool(
                request.user
                and request.user.is_authenticated
                and request.user.has_role(role)
            )

    _IsRole.__name__ = f"Is{role.title()}"
    return _IsRole


IsCustomer = IsRole("CUSTOMER")
IsVendor = IsRole("VENDOR")
IsAdministrator = IsRole("ADMINISTRATOR")
IsRider = IsRole("RIDER")


def AdminArea(area, *, write_permission=None):
    """An administrator whose tier grants `<area>.view` (reads) or `<area>.manage` (writes); see
    `apps.core.admin_permissions`. `write_permission` overrides what a non-safe method needs."""

    read_permission = f"{area}.view"
    write_permission = write_permission or f"{area}.manage"

    class _AdminArea(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if not (user and user.is_authenticated and user.has_role("ADMINISTRATOR")):
                return False
            needed = read_permission if request.method in SAFE_METHODS else write_permission
            return user.has_admin_permission(needed)

    _AdminArea.__name__ = f"AdminArea_{area}"
    return _AdminArea


class IsCustomerOrGuest(BasePermission):
    """Buying is open to anonymous guests (guest checkout) as well as Customers. A signed-in
    Vendor/Administrator/Rider is still refused: guests are not a role, only the absence of one,
    and their data is reached solely through unguessable server-issued tokens."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return True
        return user.has_role("CUSTOMER")
