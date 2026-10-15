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
        "orders.Order", on_delete=models.CASCADE, related_name="payment"
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

    def __str__(self):
        return f"Payment({self.transaction_reference})"

    @property
    def masked_msisdn(self):
        if len(self.msisdn) < 7:
            return self.msisdn
        return f"{self.msisdn[:5]}{'*' * (len(self.msisdn) - 8)}{self.msisdn[-3:]}"
