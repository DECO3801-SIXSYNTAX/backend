from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorEventViewSet

router = DefaultRouter()
router.register(r'events', VendorEventViewSet, basename='vendor-events')

urlpatterns = [
    path('', include(router.urls)),
]