from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.core.uploads import UniqueUploadTo

# `#rrggbb`; an empty string means "use the MangiMall default".
hex_color_validator = RegexValidator(
    r"^#[0-9a-fA-F]{6}$", "Enter a color as #rrggbb."
)


class Shop(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shops"
    )
    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    status_reason = models.TextField(null=True, blank=True)
    logo = models.ImageField(upload_to=UniqueUploadTo("shops/logos"), null=True, blank=True)
    primary_color = models.CharField(
        max_length=7, blank=True, default="", validators=[hex_color_validator]
    )
    accent_color = models.CharField(
        max_length=7, blank=True, default="", validators=[hex_color_validator]
    )
    # Owner-written blurb shown on the public storefront. Plain text; line breaks are kept.
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    # Per-shop override of the mall's commission percent, set only by an Administrator. Null means
    # "use `finance.PlatformSettings.default_commission_rate`".
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )

    # Where the mall disburses this shop's earnings (mobile money), set by the shop owner.
    class PayoutNetwork(models.TextChoices):
        MPESA = "MPESA", "M-Pesa"
        TIGOPESA = "TIGOPESA", "Tigo Pesa"
        AIRTEL = "AIRTEL", "Airtel Money"
        HALOPESA = "HALOPESA", "HaloPesa"

    payout_network = models.CharField(
        max_length=20, choices=PayoutNetwork.choices, blank=True, default=""
    )
    payout_phone = models.CharField(max_length=20, blank=True, default="")
    payout_account_name = models.CharField(max_length=255, blank=True, default="")

    # Pickup location for deliveries, set by the shop owner (or an Administrator). Delivery fees
    # are measured from here, so a shop without a location can't be checked out (007).
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )
    location_address = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.name

    @property
    def has_payout_details(self):
        return bool(self.payout_network and self.payout_phone and self.payout_account_name)

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    def effective_commission_rate(self):
        if self.commission_rate is not None:
            return self.commission_rate
        from apps.finance.models import PlatformSettings

        return PlatformSettings.get_solo().default_commission_rate
