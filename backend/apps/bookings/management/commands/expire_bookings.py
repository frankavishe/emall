from django.core.management.base import BaseCommand

from apps.bookings.services import expire_due_bookings, settle_stale_payments


class Command(BaseCommand):
    help = (
        "Fail timed-out mobile-money payments on bookings, then expire bookings past their "
        "response or payment deadline. Safe to run repeatedly."
    )

    def handle(self, *args, **options):
        # Payments first: a failed push stops holding its booking's time, which the second
        # step can then expire (research.md section 7).
        failed = settle_stale_payments()
        changed = expire_due_bookings()
        self.stdout.write(f"Failed {failed} stale payment(s). Expired {changed} booking(s).")
