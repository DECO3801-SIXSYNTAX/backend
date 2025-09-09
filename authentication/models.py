from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        PLANNER = "planner", "Planner"
        VENDOR = "vendor", "Vendor"
        GUEST = "guest", "Guest"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.GUEST)
