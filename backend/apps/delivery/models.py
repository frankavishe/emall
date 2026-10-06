from django.conf import settings
from django.db import models


class RiderProfile(models.Model):
    """Delivery details for an admin-registered RIDER account (`User.role == RIDER`)."""

    class VehicleType(models.TextChoices):
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        BICYCLE = "BICYCLE", "Bicycle"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rider_profile"
    )
    phone = models.CharField(max_length=32)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    plate_number = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RiderProfile({self.user_id})"
