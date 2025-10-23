from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import datetime, timezone

from .models import User
from SiPanit.firebase import get_db


def _user_doc(instance: User) -> dict:
    """Map field User Django -> dokumen Firestore."""
    return {
        "email": instance.email,
        "username": instance.username,
        "role": instance.role,
        "first_name": instance.first_name,
        "last_name": instance.last_name,
        "company": instance.company,
        "phone": instance.phone,
        "experience": instance.experience,
        "specialty": instance.specialty,
        "is_superuser": instance.is_superuser,
        "is_staff": instance.is_staff,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@receiver(post_save, sender=User)
def sync_user_to_firestore(sender, instance: User, created, **kwargs):
    """Create/Update dokumen users/{uuid} di Firestore."""
    try:
        db = get_db()
        if not db:
            return
        data = _user_doc(instance)
        if created:
            data["created_at"] = datetime.now(timezone.utc).isoformat()
        db.collection("users").document(str(instance.id)).set(data, merge=True)
    except Exception as e:
        print(f"[Firebase Sync] post_save failed for {instance.id}: {e}")


@receiver(post_delete, sender=User)
def delete_user_in_firestore(sender, instance: User, **kwargs):
    """Hapus dokumen users/{uuid} saat user dihapus di Django."""
    try:
        db = get_db()
        if not db:
            return
        db.collection("users").document(str(instance.id)).delete()
    except Exception as e:
        print(f"[Firebase Sync] post_delete failed for {instance.id}: {e}")
