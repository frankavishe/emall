from django.core.management.base import BaseCommand

from apps.bookings.services import expire_due_bookings


class Command(BaseCommand):
    help = "Expire bookings past their response or payment deadline. Safe to run repeatedly."

    def handle(self, *args, **options):
        changed = expire_due_bookings()
        self.stdout.write(f"Expired {changed} booking(s).")
