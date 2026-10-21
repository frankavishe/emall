"""Administrator tiers and what each may do (Constitution Principle I). Permissions are defined
here in code, not in database tables, so every grant is reviewable in one place and covered by
tests. Each admin area has a `.view` permission (read) and a `.manage` permission (change)."""

from django.db import models


class AdminRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    SUPPORT_ADMIN = "SUPPORT_ADMIN", "Support Admin"


class AdminPermission(models.TextChoices):
    SHOPS_VIEW = "shops.view", "View shops"
    SHOPS_MANAGE = "shops.manage", "Manage shops"
    CATALOG_VIEW = "catalog.view", "View catalog"
    CATALOG_MANAGE = "catalog.manage", "Manage catalog"
    CUSTOMERS_VIEW = "customers.view", "View customers"
    CUSTOMERS_MANAGE = "customers.manage", "Manage customers"
    ORDERS_VIEW = "orders.view", "View orders"
    ORDERS_MANAGE = "orders.manage", "Manage orders"
    RIDERS_VIEW = "riders.view", "View riders"
    RIDERS_MANAGE = "riders.manage", "Manage riders"
    FINANCE_VIEW = "finance.view", "View finance"
    FINANCE_MANAGE = "finance.manage", "Manage finance"
    REVIEWS_VIEW = "reviews.view", "View reviews"
    REVIEWS_MANAGE = "reviews.manage", "Manage reviews"
    AUDIT_VIEW = "audit.view", "View audit log"


PERMISSION_DESCRIPTIONS = {
    AdminPermission.SHOPS_VIEW: "See shops, their owners and approval status.",
    AdminPermission.SHOPS_MANAGE: "Approve or reject shops and correct shop locations.",
    AdminPermission.CATALOG_VIEW: "See every product and category.",
    AdminPermission.CATALOG_MANAGE: "Create, edit and delete categories.",
    AdminPermission.CUSTOMERS_VIEW: "See customer accounts and their recent orders.",
    AdminPermission.CUSTOMERS_MANAGE: "Block and unblock customer accounts.",
    AdminPermission.ORDERS_VIEW: "See orders and order lines.",
    AdminPermission.ORDERS_MANAGE: "Assign and unassign riders to order lines.",
    AdminPermission.RIDERS_VIEW: "See rider accounts.",
    AdminPermission.RIDERS_MANAGE: "Create, edit and deactivate riders and reset their passwords.",
    AdminPermission.FINANCE_VIEW: "See balances, payouts, transactions and finance reports.",
    AdminPermission.FINANCE_MANAGE: (
        "Change platform fees and commissions, create and retry payouts, and settle manual "
        "payments."
    ),
    AdminPermission.REVIEWS_VIEW: "See product reviews.",
    AdminPermission.REVIEWS_MANAGE: "Delete product reviews.",
    AdminPermission.AUDIT_VIEW: "See the audit log of every action taken in the mall.",
}

ROLE_PERMISSIONS = {
    AdminRole.SUPER_ADMIN: frozenset(AdminPermission),
    AdminRole.SUPPORT_ADMIN: frozenset(
        {
            AdminPermission.SHOPS_VIEW,
            AdminPermission.CATALOG_VIEW,
            AdminPermission.CUSTOMERS_VIEW,
            AdminPermission.CUSTOMERS_MANAGE,
            AdminPermission.ORDERS_VIEW,
            AdminPermission.ORDERS_MANAGE,
            AdminPermission.RIDERS_VIEW,
            AdminPermission.REVIEWS_VIEW,
            AdminPermission.REVIEWS_MANAGE,
        }
    ),
}


def permissions_for(admin_role):
    """The permissions an admin tier grants. An unknown or missing tier grants nothing."""

    return ROLE_PERMISSIONS.get(admin_role, frozenset())
