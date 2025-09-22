# project/firebase.py
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

_firebase_app = None

def init_firebase():
    """
    Initialize firebase-admin once using the service account path from settings.
    Safe to call multiple times; returns the app instance or raises on bad creds.
    """
    global _firebase_app
    if _firebase_app:
        return _firebase_app

    sa_path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT", "")
    if not sa_path:
        return None  # not configured

    cred = credentials.Certificate(sa_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app
