from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.validators import PHONE_REGEX

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


class BookingQuerySet(models.QuerySet):
    def holding(self, now=None):
        """Bookings that hold their time right now. This compares deadlines rather than trusting
        the status alone, so a time frees up on schedule even if the cleanup hasn't run."""

        now = now or timezone.now()
        return self.filter(
            models.Q(status=Booking.Status.REQUESTED, respond_by__gt=now)
            | models.Q(status=Booking.Status.AWAITING_PAYMENT, pay_by__gt=now)
            | models.Q(status=Booking.Status.CONFIRMED)
        )

    def active_unpaid(self, now=None):
        return self.holding(now).filter(
            status__in=[Booking.Status.REQUESTED, Booking.Status.AWAITING_PAYMENT]
        )

    def overlapping(self, starts_at, ends_at):
        """A booking ending exactly when the window starts doesn't overlap it."""

        return self.filter(starts_at__lt=ends_at, ends_at__gt=starts_at)

    def due_for_expiry(self, now=None):
        """The exact opposite of `holding` for unanswered and unpaid bookings."""

        now = now or timezone.now()
        return self.filter(
            models.Q(status=Booking.Status.REQUESTED, respond_by__lte=now)
            | models.Q(status=Booking.Status.AWAITING_PAYMENT, pay_by__lte=now)
        )


class Booking(models.Model):
    """A customer's request for a service at a time. Every status change goes through
    `apps.bookings.services`, with this row locked, and writes one `BookingStatusEvent`."""

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        AWAITING_PAYMENT = "AWAITING_PAYMENT", "Awaiting payment"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No-show"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    # Copied from the service, for locking and finance.
    shop = models.ForeignKey("vendors.Shop", on_delete=models.PROTECT, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    respond_by = models.DateTimeField()
    pay_by = models.DateTimeField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, validators=[RegexValidator(PHONE_REGEX)])
    customer_note = models.TextField(blank=True, default="")
    status_reason = models.TextField(blank=True, default="")
    # Fixed when the booking is requested, so later price or commission changes don't touch it.
    price = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vendor_earning = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.ForeignKey(
        "finance.Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["shop", "starts_at"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "respond_by"]),
            models.Index(fields=["status", "pay_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="booking_ends_after_it_starts",
            ),
        ]

    def __str__(self):
        return f"Booking #{self.pk}"

    def amount_due(self):
        return self.price


class BookingStatusEvent(models.Model):
    """Append-only history of a booking's status. An empty actor means the system."""

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="status_events")
    status = models.CharField(max_length=20, choices=Booking.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Booking #{self.booking_id}: {self.status}"
