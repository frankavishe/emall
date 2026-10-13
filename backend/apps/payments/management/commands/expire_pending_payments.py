from django.conf import settings
from django.core.management.base import BaseCommand

from apps.payments.outcomes import expire_stale_payments


class Command(BaseCommand):
    help = (
        "Fails mobile-money payments still pending after PAYMENT_PENDING_TIMEOUT_MINUTES and "
        "releases their reserved stock. Safe to run repeatedly (e.g. from cron every minute)."
    )

    def handle(self, *args, **options):
        expired = expire_stale_payments()
        self.stdout.write(
            f"Expired {expired} payment(s) pending longer than "
            f"{settings.PAYMENT_PENDING_TIMEOUT_MINUTES} minute(s)."
        )
