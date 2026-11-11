from django.conf import settings
from django.db import models


class PaymentRecord(models.Model):
    """The customer's payment for one `Order`, created in the same atomic transaction as the
    order (research.md §5). A synchronous (mock/card) payment is created SUCCEEDED; a declined one
    produces no row anywhere. A mobile-money payment is created PENDING and is moved to SUCCEEDED
    or FAILED only by `apps.payments.outcomes.complete_payment()`.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    class Provider(models.TextChoices):
        # Values are AzamPay's MNO `provider` names, sent to the API as-is.
        MPESA = "Mpesa", "M-Pesa"
        TIGO = "Tigo", "Mixx by Yas (Tigo Pesa)"
        AIRTEL = "Airtel", "Airtel Money"
        HALOPESA = "Halopesa", "HaloPesa"
        AZAMPESA = "Azampesa", "AzamPesa"

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="payment", null=True, blank=True
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    method = models.CharField(max_length=50)
    # What the customer paid the mall for the whole order.
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUCCEEDED
    )
    # Our own reference; for mobile money it is the `externalId` AzamPay echoes back as
    # `utilityref` in its callback.
    transaction_reference = models.CharField(max_length=64, unique=True)
    # Mobile money only (`provider_reference` is also the customer's transaction ID for Lipa
    # Namba).
    provider = models.CharField(max_length=20, choices=Provider.choices, blank=True)
    msisdn = models.CharField(max_length=15, blank=True)  # normalised 255XXXXXXXXX
    provider_reference = models.CharField(max_length=128, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    # Manual methods (cash on delivery, Lipa Namba) only: the administrator who settled it.
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(order__isnull=False) & models.Q(booking__isnull=True))
                | (models.Q(order__isnull=True) & models.Q(booking__isnull=False)),
                name="payment_has_one_target",
            ),
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(status__in=["PENDING", "SUCCEEDED"]),
                name="one_live_payment_per_booking",
            ),
        ]

    def __str__(self):
        return f"Payment({self.transaction_reference})"

    @property
    def is_booking(self):
        return self.booking_id is not None

    @property
    def is_lipa_namba(self):
        return self.method == "lipa_namba"

    @property
    def masked_msisdn(self):
        if len(self.msisdn) < 7:
            return self.msisdn
        return f"{self.msisdn[:5]}{'*' * (len(self.msisdn) - 8)}{self.msisdn[-3:]}"


class RefundDue(models.Model):
    """Money the mall owes a customer back. It is a list, not a refund system: an administrator
    sends the money by hand and then marks the entry paid (FR-027). One entry per payment and
    reason, so a repeated callback or a double click can't owe the same money twice."""

    class Reason(models.TextChoices):
        CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED", "Customer cancelled"
        PROVIDER_CANCELLED = "PROVIDER_CANCELLED", "Provider cancelled"
        ADMIN_CANCELLED = "ADMIN_CANCELLED", "Administrator cancelled"
        LATE_PAYMENT = "LATE_PAYMENT", "Paid after the booking ended"

    class Status(models.TextChoices):
        DUE = "DUE", "Due"
        PAID = "PAID", "Paid"

    payment = models.ForeignKey(PaymentRecord, on_delete=models.PROTECT, related_name="refunds")
    # No more than the payment's amount; `apps.bookings.services` checks that when it creates one.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=30, choices=Reason.choices)
    note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DUE)
    paid_reference = models.CharField(max_length=128, blank=True, default="")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["payment", "reason"], name="one_refund_per_reason"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="refund_amount_positive"),
            models.CheckConstraint(
                condition=~models.Q(status="PAID") | ~models.Q(paid_reference=""),
                name="paid_refund_has_reference",
            ),
        ]

    def __str__(self):
        return f"Refund #{self.pk} ({self.amount})"
