# SiPanit/views.py  (or wherever your health view lives)
from django.http import JsonResponse
from django.conf import settings
from SiPanit import FIREBASE_INIT_ERROR

def health(request):
    payload = {
        "status": "ok",
        "database": "ok",
        "firebase": "ok" if FIREBASE_INIT_ERROR is None else f"error: {type(FIREBASE_INIT_ERROR).__name__}: {FIREBASE_INIT_ERROR}",
        "debug": settings.DEBUG,
    }
    return JsonResponse(payload)
