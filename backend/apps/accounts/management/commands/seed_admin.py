import os

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.core.admin_permissions import AdminRole


class Command(BaseCommand):
    help = (
        "Creates (or updates) the Administrator account from ADMIN_SEED_EMAIL / "
        "ADMIN_SEED_PASSWORD / ADMIN_SEED_NAME env vars (and optional ADMIN_SEED_ROLE, default "
        "SUPER_ADMIN). Administrator accounts are "
        "provisioned this way, not through any registration endpoint."
    )

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_SEED_EMAIL")
        password = os.environ.get("ADMIN_SEED_PASSWORD")
        name = os.environ.get("ADMIN_SEED_NAME")
        admin_role = os.environ.get("ADMIN_SEED_ROLE") or AdminRole.SUPER_ADMIN

        if not email or not password or not name:
            raise CommandError(
                "ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD, and ADMIN_SEED_NAME must all be set."
            )
        if admin_role not in AdminRole.values:
            raise CommandError(f"ADMIN_SEED_ROLE must be one of {', '.join(AdminRole.values)}.")

        email = email.lower()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "role": User.Role.ADMINISTRATOR,
                "admin_role": admin_role,
                "is_email_verified": True,
            },
        )
        user.name = name
        user.role = User.Role.ADMINISTRATOR
        user.admin_role = admin_role
        user.is_email_verified = True
        user.set_password(password)
        user.save()

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} Administrator account: {email}"))
