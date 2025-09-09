import firebase_admin
from firebase_admin import auth, credentials, firestore
from django.conf import settings
import os

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def sync_user_to_firebase(user):
    # Basic Auth user data
    data = {
        "email": user.email,
        "display_name": user.get_full_name() or user.username,
        "phone_number": user.phone if user.phone else None,
    }

    try:
        try:
            fb_user = auth.get_user_by_email(user.email)
            auth.update_user(fb_user.uid, **{k: v for k, v in data.items() if v})
        except auth.UserNotFoundError:
            fb_user = auth.create_user(
                email=user.email,
                password="123456",  # Default password, or random if you prefer
                display_name=data["display_name"],
                phone_number=data["phone_number"] if user.phone else None,
            )

        # Store extra profile info in Firestore
        profile_data = {
            "id": str(user.id),
            "name": user.get_full_name() or user.username,
            "email": user.email,
            "role": user.role,
            "company": user.company,
            "phone": user.phone,
            "experience": user.experience,
            "specialty": user.specialty,
        }
        db.collection("users").document(fb_user.uid).set(profile_data, merge=True)

        print(f"[Firebase Sync] Synced {user.email} → {fb_user.uid}")

    except Exception as e:
        print(f"[Firebase Sync] ERROR syncing {user.email}: {e}")
