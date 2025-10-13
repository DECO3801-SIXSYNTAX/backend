from django.urls import path
from .views import GuestFirebaseViewSet, debug_decode_guest

guest_list_create = GuestFirebaseViewSet.as_view({"get": "list", "post": "create"})
guest_detail      = GuestFirebaseViewSet.as_view({"patch": "partial_update", "delete": "destroy"})
#guest_import_csv  = GuestFirebaseViewSet.as_view({"post": "import_csv"})
guest_toggle_ci   = GuestFirebaseViewSet.as_view({"post": "toggle"})
guest_import_csv = GuestFirebaseViewSet.as_view({"post": "import_csv", "get": "import_csv"})
guest_qr_png      = GuestFirebaseViewSet.as_view({"get": "qr"})

urlpatterns = [
    path("debug-decode-guest/", debug_decode_guest, name="guests-debug-decode-guest"),
    path("<str:event_id>/<str:pk>/qr/",guest_qr_png, name="guest-qr"),
    path("<str:event_id>/",guest_list_create, name="guest-list-create"),
    path("<str:event_id>/<str:pk>/",guest_detail,name="guest-detail"),
    path("<str:event_id>/import-csv/",guest_import_csv, name="guest-import-csv"),
    #path("<str:event_id>/toggle-checkin/",guest_toggle_ci, name="guest-toggle-checkin"),
    
]
