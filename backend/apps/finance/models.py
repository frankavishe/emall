from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

DEFAULT_COMMISSION_RATE = Decimal("10.00")


class PlatformSettings(models.Model):
    """Single row (pk=1) of mall-wide money settings, edited only by Administrators."""

    default_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_COMMISSION_RATE,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name_plural = "platform settings"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(default_commission_rate__gte=0)
                & models.Q(default_commission_rate__lte=100),
                name="platform_commission_rate_0_100",
            ),
        ]

    def __str__(self):
        return f"PlatformSettings(commission={self.default_commission_rate}%)"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Payout(models.Model):
    """One disbursement of a shop's available earnings, created only by
    `finance.services.create_payout()`. The order lines it pays are `self.items`; the destination
    is snapshotted so later edits to the shop's payout details don't rewrite history."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    shop = models.ForeignKey("vendors.Shop", on_delete=models.PROTECT, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    network = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    provider_reference = models.CharField(max_length=128, null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payouts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout({self.pk}, shop={self.shop_id}, {self.amount}, {self.status})"

    @property
    def reference(self):
        return f"PAYOUT-{self.pk}"
