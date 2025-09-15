from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from authentication.views import UserViewSet

def api_root(request):
    return JsonResponse({
        "message": "SiPanit API is running",
        "endpoints": {
            "users": "/users/",
            "auth": "/api/auth/",
            "admin": "/admin/"
        }
    })

router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("authentication.urls")),
] + router.urls
