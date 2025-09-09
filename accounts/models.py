from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        PLANNER = "PLANNER", "Planner"
        VENDOR = "VENDOR", "Vendor"
        GUEST = "GUEST", "Guest"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)

 #added features
    phone = models.CharField(max_length=30, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    experience = models.CharField(max_length=255, blank=True, null=True)
    specialty = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
