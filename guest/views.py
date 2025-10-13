# guests/views.py
from .permissions import IsPlannerorAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
import csv, io

from .serializers import GuestSerializer
from .repository import upsert_guest, delete_guest, list_guests, toggle_checkin

class GuestFirebaseViewSet(viewsets.ViewSet):
    """
    /api/guests (GET, POST)
    /api/guests/{id} (PATCH, DELETE)
    /api/guests/toggle-checkin (POST)
    /api/guests/import-csv (POST multipart)
    """

    permission_classes = [IsAuthenticated, IsPlannerorAdmin]

    def list(self, request, event_id=None):
        q        = request.query_params.get("q")
        tags_any = request.query_params.getlist("tags") or None
        limit    = int(request.query_params.get("limit", 50))
        page_tok = request.query_params.get("pageToken")

        items, next_token = list_guests(event_id, q=q, tags_any=tags_any, limit=limit, page_token=page_tok)
        return Response({"items": items, "nextPageToken": next_token})

    def create(self, request, event_id=None):
        data = {**request.data, "eventId": event_id}   # force scope by path
        data.pop("seat", None)                          # seat assigned later
        ser = GuestSerializer(data=data)
        ser.is_valid(raise_exception=True)
        gid = upsert_guest(event_id, ser.validated_data)
        return Response({"id": gid}, status=201)

    def partial_update(self, request, pk=None, event_id=None):
        data = {**request.data, "id": pk, "eventId": event_id}
        ser = GuestSerializer(data=data, partial=True)
        ser.is_valid(raise_exception=True)
        gid = upsert_guest(event_id, ser.validated_data)
        return Response({"id": gid})

    def destroy(self, request, pk=None, event_id=None):
        delete_guest(event_id, pk)
        return Response(status=204)


    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser], url_path="import-csv")
    def import_csv(self, request):
        """
        form-data: file=<csv>, eventId=<id>
        CSV headers (exactly):
          name,email,phone,dietary_restriction,accessibility_needs
        seat is NOT in the template; it will be assigned later by the layout editor.
        tags are computed from dietary_restriction + accessibility_needs.
        """
        file = request.data.get("file")
        event_id = request.data.get("eventId")
        if not file or not event_id:
            return Response({"detail": "file and eventId are required"}, status=400)

        reader = csv.DictReader(io.TextIOWrapper(file, encoding="utf-8"))
        imported, skipped = 0, []

        for idx, row in enumerate(reader, start=2):
            name  = (row.get("name")  or "").strip()
            email = (row.get("email") or "").strip().lower()
            if not name or not email:
                skipped.append({"line": idx, "reason": "missing name or email"})
                continue

            phone   = (row.get("phone") or "").strip()
            dietary = (row.get("dietary_restriction") or "").strip()
            access  = (row.get("accessibility_needs") or "").strip()

            payload = {
                "eventId": event_id,
                "name": name,
                "email": email,
                "phone": phone,
                "dietaryRestriction": dietary,
                "accessibilityNeeds": access,
            }
            upsert_guest(event_id, payload)
            imported += 1

        return Response({"imported": imported, "skipped": skipped}, status=201)
