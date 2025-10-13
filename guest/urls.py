from django.urls import path
from .views import GuestFirebaseViewSet

guest_list_create = GuestFirebaseViewSet.as_view({"get": "list", "post": "create"})
guest_detail      = GuestFirebaseViewSet.as_view({"patch": "partial_update", "delete": "destroy"})
guest_import_csv  = GuestFirebaseViewSet.as_view({"post": "import_csv"})
guest_toggle_ci   = GuestFirebaseViewSet.as_view({"post": "toggle"})

urlpatterns = [
    # Collection for an event
    path("<str:event_id>/",                 guest_list_create, name="guest-list-create"),
    # Detail within an event
    path("<str:event_id>/<str:pk>/",        guest_detail,      name="guest-detail"),
    # CSV import scoped to event
    path("<str:event_id>/import-csv/",      guest_import_csv,  name="guest-import-csv"),
    # Toggle check-in scoped to event
    path("<str:event_id>/toggle-checkin/",  guest_toggle_ci,   name="guest-toggle-checkin"),
]
