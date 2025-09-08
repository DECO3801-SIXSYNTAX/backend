from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

ROLES = ["Admin", "Planner", "Vendor", "Guest"]

class Command(BaseCommand):
    help = "Create default roles (Groups): Admin, Planner, Vendor, Guest"

    def handle(self, *args, **options):
        created, existed = 0, 0
        for name in ROLES:
            obj, is_created = Group.objects.get_or_create(name=name)
            created += int(is_created)
            existed += int(not is_created)
        self.stdout.write(self.style.SUCCESS(
            f"Roles ready. created={created}, existed={existed}"
        ))
