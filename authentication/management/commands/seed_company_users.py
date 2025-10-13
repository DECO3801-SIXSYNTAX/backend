from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

TEST_PREFIX = "demo_"        # supaya gampang dihapus
DEFAULT_PASSWORD = "Passw0rd!"  # password semua akun seed

USERS = [
    # Company A
    {"username": f"{TEST_PREFIX}adminA",   "email": "adminA@compa.test",   "role": "admin",   "company": "COMP_A", "first_name": "Admin",   "last_name": "A"},
    {"username": f"{TEST_PREFIX}plannerA", "email": "plannerA@compa.test", "role": "planner", "company": "COMP_A", "first_name": "Planner", "last_name": "A"},
    {"username": f"{TEST_PREFIX}vendorA",  "email": "vendorA@compa.test",  "role": "vendor",  "company": "COMP_A", "first_name": "Vendor",  "last_name": "A"},

    # Company B
    {"username": f"{TEST_PREFIX}adminB",   "email": "adminB@compb.test",   "role": "admin",   "company": "COMP_B", "first_name": "Admin",   "last_name": "B"},
    {"username": f"{TEST_PREFIX}plannerB", "email": "plannerB@compb.test", "role": "planner", "company": "COMP_B", "first_name": "Planner", "last_name": "B"},
    {"username": f"{TEST_PREFIX}vendorB",  "email": "vendorB@compb.test",  "role": "vendor",  "company": "COMP_B", "first_name": "Vendor",  "last_name": "B"},
]

class Command(BaseCommand):
    help = "Seed demo users per company for quick Postman testing."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded demo_ users first")

    def handle(self, *args, **opts):
        if opts["reset"]:
            qs = User.objects.filter(username__startswith=TEST_PREFIX)
            n = qs.count()
            qs.delete()
            self.stdout.write(self.style.WARNING(f"Deleted {n} existing demo users."))

        created, existed = 0, 0
        for data in USERS:
            user, is_created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "role": data["role"],
                    "company": (data.get("company") or "").strip().upper(),
                    "is_staff": data["role"] == "admin",        # admin convenience
                    "is_superuser": data["role"] == "admin",
                },
            )
            if is_created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                created += 1
            else:
                # keep idempotent but ensure fields are up to date
                user.email = data["email"]
                user.first_name = data.get("first_name", "")
                user.last_name = data.get("last_name", "")
                user.role = data["role"]
                user.company = (data.get("company") or "").strip().upper()
                user.is_staff = data["role"] == "admin"
                user.is_superuser = data["role"] == "admin"
                user.save()
                existed += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete. created={created}, updated={existed}"))
        self.stdout.write(self.style.NOTICE(f"Default password for all: {DEFAULT_PASSWORD}"))
        self.stdout.write(self.style.HTTP_INFO("Users:"))
        for u in USERS:
            self.stdout.write(f" - {u['username']:>14} | {u['role']:<7} | {u['company']} | {u['email']}")