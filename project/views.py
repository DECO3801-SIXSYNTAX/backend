# project/views.py
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings
from project.firebase import init_firebase

def health(request):
    # --- DB check ---
    db_ok = True
    try:
        connections['default'].cursor()
    except OperationalError:
        db_ok = False

    # --- Firebase check ---
    fb_status = "not-configured"
    if settings.FIREBASE_SERVICE_ACCOUNT:
        try:
            app = init_firebase()
            fb_status = "ok" if app is not None else "not-configured"
        except Exception as e:
            fb_status = f"error: {e.__class__.__name__}"

    return JsonResponse({
        "status": "ok",
        "database": "ok" if db_ok else "error",
        "firebase": fb_status,
        "debug": bool(getattr(settings, "DEBUG", False)),
    })
