from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from SiPanit.views import health
from authentication.views import UserViewSet

# DRF Router
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

# Simple API root
def api_root(request):
    return JsonResponse({
        "message": "SiPanit API is running",
        "endpoints": {
            "users": "/api/users/",
            "auth": "/api/auth/",
            "admin": "/admin/",
            "health": "/api/health/"
        }
    })

urlpatterns = [
    # Root landing
    path("", api_root, name="api-root"),

    # Admin
    path("admin/", admin.site.urls),

    # Health check
    path("api/health/", health),

    # JWT endpoints
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # App routes
    path("api/auth/", include("authentication.urls")),
    #path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),

    # DRF router (users, etc.)
    path("api/", include(router.urls)),

    path("api/event/", include("event.urls")),
]
