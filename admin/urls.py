from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminEventsViewSet, AdminUsersViewSet, AdminMetaViewSet

router = DefaultRouter()
router.register(r"admin/events", AdminEventsViewSet, basename="admin-events")
router.register(r"admin/users", AdminUsersViewSet, basename="admin-users")

urlpatterns = [
    path("api/", include(router.urls)),
]
