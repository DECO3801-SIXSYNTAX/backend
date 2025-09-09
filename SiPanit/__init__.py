# SiPanit/__init__.py
import os
import firebase_admin
from firebase_admin import credentials

# Exported so other modules (e.g., SiPanit.views) can read it
FIREBASE_INIT_ERROR: str | None = None

sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if not firebase_admin._apps:  # only init once
    if not sa_path:
        FIREBASE_INIT_ERROR = "FIREBASE_SERVICE_ACCOUNT env var not set"
        print(f"[Firebase] Skipped init: {FIREBASE_INIT_ERROR}")
    else:
        try:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
            print("[Firebase] Admin SDK initialized")
        except Exception as e:
            FIREBASE_INIT_ERROR = str(e)
            print(f"[Firebase] Initialization failed: {FIREBASE_INIT_ERROR}")
