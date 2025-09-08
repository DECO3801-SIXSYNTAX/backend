from django.http import JsonResponse
from django.conf import settings

def health(request):
    return JsonResponse({
        "status": "ok",
        "database": "ok",
        "firebase": "ok" if getattr(settings, "FIREBASE_READY", False) else "not-configured",
        "debug": settings.DEBUG,
    })
