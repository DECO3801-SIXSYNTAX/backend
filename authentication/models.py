from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        PLANNER = "planner", "Planner"
        VENDOR = "vendor", "Vendor"
        GUEST = "guest", "Guest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.GUEST)

    # Planner-specific fields (optional, only used when role='planner')
    company = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    specialty = models.CharField(max_length=255, blank=True, null=True)
