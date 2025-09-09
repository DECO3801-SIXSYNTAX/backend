from django.contrib import admin
from django.urls import path, include
from SiPanit.views import health
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", health),  # optional root -> shows the health JSON
    path('admin/', admin.site.urls),
    path('api/health/', health),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/', include('accounts.urls')),
    path('api/admin/', include("adminapi.urls")),
    path('api/events/', include('events.urls')),
]
