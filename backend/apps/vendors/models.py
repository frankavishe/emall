from django.conf import settings
from django.core.validators import RegexValidator
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
    created_at = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
