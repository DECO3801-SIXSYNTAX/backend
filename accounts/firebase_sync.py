from firebase_admin import auth
from SiPanit.firebase import init_firebase

def sync_user_to_firebase(user):
    """
    Sync a Django user to Firebase Auth.
    - If user exists → update
    - If not → create a new one
    - Always set custom claims (role)
    """
    init_firebase()

    try:
        # Check if the user already exists in Firebase
        fb_user = auth.get_user_by_email(user.email)
        # Update existing Firebase user
        fb_user = auth.update_user(
            fb_user.uid,
            email=user.email,
            display_name=user.get_full_name() or user.username,
            disabled=not user.is_active,
        )
        print(f"[Firebase Sync] Updated user {user.email} in Firebase")
    except auth.UserNotFoundError:
        # Create new Firebase user
        fb_user = auth.create_user(
            uid=str(user.id),  # Use Django UUID as Firebase UID
            email=user.email,
            display_name=user.get_full_name() or user.username,
            password="ChangeMe123!",  # Default password; should reset via Firebase
        )
        print(f"[Firebase Sync] Created user {user.email} in Firebase")

    # ✅ Set custom claims for role
    try:
        auth.set_custom_user_claims(
            fb_user.uid,
            {"role": user.role}
        )
        print(f"[Firebase Sync] Set role={user.role} for {user.email}")
    except Exception as e:
        print(f"[Firebase Sync] Failed to set claims for {user.email}: {e}")

    return fb_user
