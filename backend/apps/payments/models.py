from django.db import models


class PaymentRecord(models.Model):
    """Only ever created alongside a successfully created `Order`, in the same atomic transaction
    (research.md §5) — a failed mock payment attempt produces no row anywhere.
    """

    class Status(models.TextChoices):
        SUCCEEDED = "SUCCEEDED", "Succeeded"

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="payment"
    )
    method = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUCCEEDED
    )
    transaction_reference = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment({self.transaction_reference})"
