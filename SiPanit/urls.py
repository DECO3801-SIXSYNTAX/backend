from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from SiPanit.views import health
from authentication.views import UserViewSet

# ---- DRF router (company-scoped users) ----
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

def api_root(request):
    return JsonResponse({
        "message": "SiPanit API is running",
        "endpoints": {
            "users": "/api/users/",
            "auth": "/api/auth/",
            "admin": "/admin/",
            "vendor": "/api/vendor/",
            "guests": "/api/guests/",
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

    # Auth (JWT and custom auth routes)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("authentication.urls")),  # register/login/reset, etc.

    # Domain APIs
    path("api/events/", include("events.urls")),  # your 'events' app
    path("api/event/", include("event.urls")),    # your 'event' app (layouts etc.)

    # DRF router (users listing, retrieve, create, etc.)
    path("api/", include(router.urls)),

    path("api/event/", include("event.urls")),
    path("api/admin/", include("adminapi.urls")),
    path("api/guest/", include("guest.urls")),  # Consistent plural form
    path("api/guests/", include("guest.urls")),  # Consistent plural form
    path("api/vendor/", include("vendor.urls")),
]   