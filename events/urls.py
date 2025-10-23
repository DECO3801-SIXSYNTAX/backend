from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, GuestViewSet
router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'guests', GuestViewSet, basename='guest')
urlpatterns = [ path('', include(router.urls)) ]
