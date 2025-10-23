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
    
    # Check if app already exists (either in global or in firebase_admin._apps)
    if _app:
        return _app
    
    # If firebase_admin already initialized but _app not set, retrieve it
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    # Check if using Firebase Emulator
    use_emulator = os.getenv("FIREBASE_EMULATOR", "0") == "1"
    project_id = os.getenv("FIREBASE_PROJECT_ID", "sipanit-dev")
    
    if use_emulator:
        # For emulator mode, we don't need real credentials
        # Just set the environment variables for emulator hosts
        if not os.getenv("FIRESTORE_EMULATOR_HOST"):
            os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
        if not os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
            os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = "127.0.0.1:9099"
        
        # Initialize with default credentials for emulator
        _app = firebase_admin.initialize_app(options={
            "projectId": project_id
        })
    else:
        # Production mode - use real credentials
        cred_path = os.getenv("FIREBASE_CREDENTIALS")
        if not cred_path:
            raise RuntimeError("FIREBASE_CREDENTIALS not set in .env")

        base_dir = Path(__file__).resolve().parent.parent
        cred_file = (base_dir / cred_path) if not os.path.isabs(cred_path) else Path(cred_path)

        if not cred_file.exists():
            raise FileNotFoundError(f"Service account file not found: {cred_file}")

        cred = credentials.Certificate(str(cred_file))
        _app = firebase_admin.initialize_app(cred, {
            "projectId": project_id
        })

    return _app


def get_db():
    """Return Firestore client (auto init kalau belum)."""
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.client()
    return _db
