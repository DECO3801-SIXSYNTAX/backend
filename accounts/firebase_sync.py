# accounts/firebase_sync.py
from __future__ import annotations

import logging
from typing import Optional

import firebase_admin  # ensures package is present
from firebase_admin import auth, firestore

logger = logging.getLogger(__name__)


def _db():
    """Get a Firestore client (assumes Firebase Admin already initialized)."""
    return firestore.client()


def upsert_user_in_auth_and_firestore(user) -> Optional[str]:
    """
    Create or update the Firebase Auth user + Firestore 'users' document
    for the given Django user. Returns Firebase UID (or None on failure).
    """
    if not user.email:
        logger.warning("[Firebase Sync] skipped: user %s has no email", user.pk)
        return None

    # --- Auth: create or update by email ---
    try:
        fb_user = auth.get_user_by_email(user.email)
        # Keep display name/email updated
        fb_user = auth.update_user(
            fb_user.uid,
            email=user.email,
            display_name=(user.get_full_name() or user.username),
        )
        created = False
    except auth.UserNotFoundError:
        fb_user = auth.create_user(
            email=user.email,
            display_name=(user.get_full_name() or user.username),
        )
        created = True

    uid = fb_user.uid
    logger.info(
        "[Firebase Sync] %s Firebase Auth user %s (%s)",
        "created" if created else "updated",
        user.email,
        uid,
    )

    # --- Firestore: upsert profile document ---
    doc = {
        "id": str(user.id),
        "name": (user.get_full_name() or user.username or ""),
        "email": user.email,
        "role": getattr(user, "role", None),
        "phone": getattr(user, "phone", None),
        "company": getattr(user, "company", None),
        "experience": getattr(user, "experience", None),
        "specialty": getattr(user, "specialty", None),
    }
    _db().collection("users").document(uid).set(doc, merge=True)
    logger.info("[Firebase Sync] upserted Firestore profile for %s", user.email)

    return uid


def delete_user_in_auth_and_firestore(user) -> None:
    """
    Delete the corresponding Firebase Auth user and Firestore profile.
    We look up by email (since we don't store UID on the Django model).
    """
    if not user.email:
        logger.warning("[Firebase Delete] skipped: user %s has no email", user.pk)
        return

    uid = None
    try:
        fb_user = auth.get_user_by_email(user.email)
        uid = fb_user.uid
        auth.delete_user(uid)
        logger.info("[Firebase Delete] removed Auth user %s (%s)", user.email, uid)
    except auth.UserNotFoundError:
        logger.info("[Firebase Delete] Auth user not found for %s", user.email)

    # Remove Firestore doc (use UID if known; otherwise best-effort by email)
    db = _db()
    if uid:
        db.collection("users").document(uid).delete()
        logger.info("[Firebase Delete] removed Firestore doc uid=%s", uid)
    else:
        # Optional fallback: delete any docs that match the email
        for snap in db.collection("users").where("email", "==", user.email).stream():
            snap.reference.delete()
            logger.info("[Firebase Delete] removed Firestore doc by email=%s", user.email)
