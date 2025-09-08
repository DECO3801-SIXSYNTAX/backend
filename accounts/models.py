from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN","Admin"
        PLANNER = "PLANNER","Planner"
        VENDOR = "VENDOR","Vendor"
        GUEST = "GUEST","Guest"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    def __str__(self): return f"{self.username} ({self.role})"
