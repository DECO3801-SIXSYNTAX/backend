from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

# Extra imports for Firebase sync
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
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)

    def __str__(self):
        return f"{self.username} ({self.role})"


# 🔔 Signal to sync Django User → Firebase
@receiver(post_save, sender=User)
def sync_user_after_save(sender, instance, created, **kwargs):
    """
    Whenever a user is created/updated in Django,
    try to sync it to Firebase Auth.
    """
    if not instance.email:  # Firebase requires email
        return

    try:
        sync_user_to_firebase(instance)
    except Exception as e:
        print(f"[Firebase Sync] Failed to sync {instance.email}: {e}")
