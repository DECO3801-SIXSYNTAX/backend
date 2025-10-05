# SiPanit/firebase.py
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

_app = None
_db = None

def init_firebase():
    """
    Initialize firebase-admin once using FIREBASE_CREDENTIALS from .env.
    Safe dipanggil berkali-kali.
    """
    global _app
    if _app:
        return _app

    cred_path = os.getenv("FIREBASE_CREDENTIALS")
    if not cred_path:
        raise RuntimeError("FIREBASE_CREDENTIALS not set in .env")

    base_dir = Path(__file__).resolve().parent.parent
    cred_file = (base_dir / cred_path) if not os.path.isabs(cred_path) else Path(cred_path)

    if not cred_file.exists():
        raise FileNotFoundError(f"Service account file not found: {cred_file}")

    if not firebase_admin._apps:  # hanya init sekali
        cred = credentials.Certificate(str(cred_file))
        _app = firebase_admin.initialize_app(cred, {
            "projectId": os.getenv("FIREBASE_PROJECT_ID")
        })
    else:
        _app = firebase_admin.get_app()

    return _app


def get_db():
    """Return Firestore client (auto init kalau belum)."""
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.client()
    return _db
