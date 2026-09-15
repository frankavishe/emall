"""Server-side role checks (Constitution Principle I: enforced on every request; client-side role
checks MUST NOT be relied upon for authorization).
"""

from rest_framework.permissions import BasePermission


def IsRole(role):
    class _IsRole(BasePermission):
        def has_permission(self, request, view):
            return bool(
                request.user
                and request.user.is_authenticated
                and request.user.role == role
            )

    _IsRole.__name__ = f"Is{role.title()}"
    return _IsRole


IsCustomer = IsRole("CUSTOMER")
IsVendor = IsRole("VENDOR")
IsAdministrator = IsRole("ADMINISTRATOR")
