from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from .firebase_sync import sync_user_to_firebase

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        PLANNER = "PLANNER", "Planner"
        VENDOR = "VENDOR", "Vendor"
        GUEST = "GUEST", "Guest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=False)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    company = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    experience = models.CharField(max_length=100, blank=True, null=True)
    specialty = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

@receiver(post_save, sender=User)
def sync_user_after_save(sender, instance, created, **kwargs):
    if not instance.email:
        return
    try:
        sync_user_to_firebase(instance)
    except Exception as e:
        print(f"[Firebase Sync] Failed to sync {instance.email}: {e}")
