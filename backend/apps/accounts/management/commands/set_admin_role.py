from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.audit.models import AuditAction
from apps.audit.services import record
from apps.core.admin_permissions import AdminRole


class Command(BaseCommand):
    help = (
        "Sets an Administrator's tier (SUPER_ADMIN or SUPPORT_ADMIN), which decides the admin "
        "areas they may see and change. Tiers are not self-service and have no endpoint."
    )

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("admin_role", choices=AdminRole.values)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        admin_role = options["admin_role"]
        user = User.objects.filter(email=email, role=User.Role.ADMINISTRATOR).first()
        if user is None:
            raise CommandError(f"No Administrator account with email {email}.")

        previous = user.admin_role
        if previous != admin_role:
            user.admin_role = admin_role
            user.save(update_fields=["admin_role"])
            record(
                AuditAction.ADMIN_ROLE_CHANGED,
                target=user,
                metadata={"from": previous, "to": admin_role},
            )
        self.stdout.write(
            self.style.SUCCESS(f"{email} is now {AdminRole(admin_role).label}.")
        )
