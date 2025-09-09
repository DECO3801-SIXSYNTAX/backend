from django.contrib import admin
from django.urls import path, include
from project.views import health
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", health),  # optional root -> shows the health JSON
    path("admin/", admin.site.urls),
    path("api/health/", health),

    # JWT endpoints (username/password or future custom views)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # App routes
    path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
]
