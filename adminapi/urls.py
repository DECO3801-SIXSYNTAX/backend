from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUsersViewSet, AdminEventsViewSet

router = DefaultRouter()  # trailing slash required
router.register(r'users',  AdminUsersViewSet, basename='admin-users')
router.register(r'events', AdminEventsViewSet, basename='admin-events')


urlpatterns = [
    path('', include(router.urls)),  # exposes: users/, events/, meta/
]
