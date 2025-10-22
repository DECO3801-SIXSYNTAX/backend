from django.urls import path
from .views import GuestFirebaseViewSet, debug_decode_guest, bulk_send_invites

guest_list_create = GuestFirebaseViewSet.as_view({"get": "list", "post": "create"})
guest_detail      = GuestFirebaseViewSet.as_view({"patch": "partial_update", "delete": "destroy"})
guest_import_csv  = GuestFirebaseViewSet.as_view({"post": "import_csv"})
#guest_toggle_ci   = GuestFirebaseViewSet.as_view({"post": "toggle"})
#guest_import_csv = GuestFirebaseViewSet.as_view({"post": "import_csv", "get": "import_csv"})
guest_qr_png      = GuestFirebaseViewSet.as_view({"get": "qr"})
send_invite     = GuestFirebaseViewSet.as_view({"post": "send_invite"})
# bulk_send_invites = GuestFirebaseViewSet.as_view({"post": "bulk_send_invites"})
assign_seat        = GuestFirebaseViewSet.as_view({"patch": "assign_seat"})

urlpatterns = [
    path("debug-decode-guest/", debug_decode_guest, name="guests-debug-decode-guest"),
    path("bulk-send-invites/<str:event_id>/", bulk_send_invites, name="guest-bulk-send-invites"),
    path("import-csv/<str:event_id>/",guest_import_csv, name="guest-import-csv"),
    path("qr/<str:event_id>/<str:pk>/",guest_qr_png, name="guest-qr"),
    path("<str:event_id>/<str:pk>/",guest_detail,name="guest-detail"),
    path("<str:event_id>/",guest_list_create, name="guest-list-create"),
    path("<str:event_id>/<str:guest_id>/send-invite/", send_invite, name="guest-send-invite"),
    path("assign-seat/<str:event_id>/<str:pk>/",   assign_seat,   name="guest-assign-seat"),
    #path("<str:event_id>/toggle-checkin/",guest_toggle_ci, name="guest-toggle-checkin"),
    
]
