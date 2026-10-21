from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditAction(models.TextChoices):
    """The one catalog of audited actions. Names are `<area>.<verb>`, so the admin log can
    filter a whole area by prefix (e.g. `shop.`)."""

    # Auth and account
    LOGIN = "auth.login", "Signed in"
    LOGIN_FAILED = "auth.login_failed", "Failed sign-in"
    LOGOUT = "auth.logout", "Signed out"
    REGISTERED = "auth.registered", "Registered"
    EMAIL_VERIFIED = "auth.email_verified", "Verified email"
    PASSWORD_RESET_REQUESTED = "auth.password_reset_requested", "Requested password reset"
    PASSWORD_RESET_COMPLETED = "auth.password_reset_completed", "Reset password"
    # Customers and riders (admin)
    CUSTOMER_BLOCKED = "customer.blocked", "Blocked customer"
    CUSTOMER_UNBLOCKED = "customer.unblocked", "Unblocked customer"
    RIDER_CREATED = "rider.created", "Created rider"
    RIDER_UPDATED = "rider.updated", "Updated rider"
    RIDER_DEACTIVATED = "rider.deactivated", "Deactivated rider"
    RIDER_PASSWORD_RESET = "rider.password_reset", "Reset rider password"
    # Shops
    SHOP_CREATED = "shop.created", "Opened shop"
    SHOP_APPROVED = "shop.approved", "Approved shop"
    SHOP_REJECTED = "shop.rejected", "Rejected shop"
    SHOP_LOCATION_UPDATED = "shop.location_updated", "Updated shop location"
    SHOP_PROFILE_UPDATED = "shop.profile_updated", "Updated shop profile"
    SHOP_COMMISSION_SET = "shop.commission_set", "Set shop commission"
    # Catalog
    CATEGORY_CREATED = "category.created", "Created category"
    CATEGORY_UPDATED = "category.updated", "Updated category"
    CATEGORY_DELETED = "category.deleted", "Deleted category"
    PRODUCT_CREATED = "product.created", "Created product"
    PRODUCT_UPDATED = "product.updated", "Updated product"
    PRODUCT_DELETED = "product.deleted", "Deleted product"
    PRODUCT_PUBLISHED = "product.published", "Published product"
    PRODUCT_UNPUBLISHED = "product.unpublished", "Unpublished product"
    REVIEW_DELETED = "review.deleted", "Deleted review"
    # Orders
    ORDER_PLACED = "order.placed", "Placed order"
    ORDER_ITEM_STATUS_CHANGED = "order_item.status_changed", "Changed order line status"
    ORDER_ITEM_RIDER_ASSIGNED = "order_item.rider_assigned", "Assigned rider"
    ORDER_ITEM_RIDER_UNASSIGNED = "order_item.rider_unassigned", "Unassigned rider"
    # Payments
    PAYMENT_CONFIRMED = "payment.confirmed", "Confirmed payment"
    PAYMENT_REJECTED = "payment.rejected", "Rejected payment"
    PAYMENT_COMPLETED = "payment.completed", "Payment completed"
    PAYMENT_FAILED = "payment.failed", "Payment failed"
    PAYMENT_EXPIRED = "payment.expired", "Payment expired"
    # Finance
    SETTINGS_UPDATED = "settings.updated", "Updated platform settings"
    PAYOUT_CREATED = "payout.created", "Created payout"
    PAYOUT_RETRIED = "payout.retried", "Retried payout"
    PAYOUT_DETAILS_UPDATED = "payout_details.updated", "Updated payout details"


class AuditEvent(models.Model):
    """One append-only row per audited action. Actor and target are snapshotted as text so the
    row stays readable after the user or object is changed or deleted. Written only through
    `apps.audit.services.record`; nothing updates or deletes these rows."""

    SYSTEM_ROLE = "SYSTEM"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Null for system events (payment callbacks, expiry) and anonymous callers (failed sign-in).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_email = models.CharField(max_length=254, blank=True, default="")
    actor_role = models.CharField(max_length=20, blank=True, default="")
    action = models.CharField(max_length=64, choices=AuditAction.choices)
    target_type = models.CharField(max_length=32, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    target_repr = models.CharField(max_length=255, blank=True, default="")
    # Reasons, before/after values, changed field names. Never passwords, tokens or account
    # numbers.
    metadata = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_email or self.actor_role or 'anonymous'}"
