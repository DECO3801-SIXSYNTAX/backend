# event/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EventViewSet,
    LayoutSaveView,
    LayoutReadView,
    LayoutMetaView,
)

router = DefaultRouter()
router.register(r"", EventViewSet, basename="event")

urlpatterns = [
    path("", include(router.urls)),

    # Layout (FE format)
    path("layouts/save/", LayoutSaveView.as_view(), name="layout-save"),
    path("layouts/<str:event_id>/", LayoutReadView.as_view(), name="layout-read"),
    path("layouts/meta/<str:event_id>/", LayoutMetaView.as_view(), name="layout-meta"),
]