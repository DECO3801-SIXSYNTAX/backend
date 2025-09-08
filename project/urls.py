from django.contrib import admin
from django.urls import path, include
from project.views import health
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", health),  # optional root
    path("admin/", admin.site.urls),
    path("api/health/", health),

    # ✅ JWT endpoints
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ✅ delegate to apps
    path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
]
