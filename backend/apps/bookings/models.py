from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MIN_SERVICE_MINUTES = 30
MAX_SERVICE_MINUTES = 24 * 60


class ServiceQuerySet(models.QuerySet):
    def visible(self):
        """What the public can see and book: published services of APPROVED shops."""

        return self.filter(is_published=True, is_archived=False, shop__status="APPROVED")


class Service(models.Model):
    """Something a services shop offers. Archiving replaces deleting, because bookings will keep
    pointing at it."""

    shop = models.ForeignKey("vendors.Shop", on_delete=models.PROTECT, related_name="services")
    category = models.ForeignKey(
        "catalog.Category", on_delete=models.PROTECT, related_name="services"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_SERVICE_MINUTES), MaxValueValidator(MAX_SERVICE_MINUTES)]
    )
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        constraints = [
            # An archived service's name is free to use again.
            models.UniqueConstraint(
                fields=["shop", "name"],
                condition=models.Q(is_archived=False),
                name="unique_active_service_name_per_shop",
            ),
            models.CheckConstraint(condition=models.Q(price__gt=0), name="service_price_positive"),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gte=MIN_SERVICE_MINUTES)
                & models.Q(duration_minutes__lte=MAX_SERVICE_MINUTES),
                name="service_duration_in_range",
            ),
        ]

    def __str__(self):
        return self.name


class OpeningHours(models.Model):
    """One period a shop is open on a weekday, in local market time. Periods on one day can't
    overlap (ShopScheduleSerializer), and a day can have several, to leave room for a break."""

    shop = models.ForeignKey(
        "vendors.Shop", on_delete=models.CASCADE, related_name="opening_hours"
    )
    # 0 is Monday, matching `date.weekday()`.
    weekday = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    opens_at = models.TimeField()
    closes_at = models.TimeField()

    class Meta:
        verbose_name_plural = "opening hours"
        ordering = ["weekday", "opens_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(closes_at__gt=models.F("opens_at")),
                name="opening_hours_close_after_open",
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__lte=6), name="opening_hours_weekday_in_range"
            ),
        ]

    def __str__(self):
        return f"{self.shop_id}: {self.weekday} {self.opens_at}-{self.closes_at}"


class ShopClosure(models.Model):
    """A whole local date when a shop is closed."""

    shop = models.ForeignKey("vendors.Shop", on_delete=models.CASCADE, related_name="closures")
    date = models.DateField()
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "date"], name="unique_closure_per_shop_date"),
        ]

    def __str__(self):
        return f"{self.shop_id}: {self.date}"
