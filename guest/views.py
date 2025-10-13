# guests/views.py
from .permissions import IsPlannerorAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import csv, io
from django.http import HttpResponse

from .serializers import GuestSerializer
from .repository import get_guest, upsert_guest, delete_guest, list_guests, toggle_checkin

from crypto.qr import encrypt_payload, qr_png_bytes, decrypt_payload, decrypt_to_guest
from django.conf import settings
from django.utils.text import slugify

from urllib.parse import urlparse, parse_qs
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny   # use IsAuthenticated later if you want
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from crypto.qr import decrypt_payload, decrypt_to_guest
from .repository import get_guest

def _extract_token(raw):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        u = urlparse(s)
        if u.scheme and u.netloc:
            return parse_qs(u.query).get("token", [None])[0]
    except Exception:
        pass
    return s

@api_view(["POST","GET"])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def debug_decode_guest(request):
    raw = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
    print(raw,'raw')
    token = _extract_token(raw)
    if not token:
        return Response({"detail": "Token required (JSON/form 'token' or ?token=...)"}, status=400)
    try:
        payload = decrypt_payload(token)            # {"e": "...", "g": "..."}
        guest   = decrypt_to_guest(token, get_guest)
        return Response({"payload": payload, "guest": guest})
    except ValueError as e:
        return Response({"detail": str(e)}, status=401)
    except LookupError as e:
        return Response({"detail": str(e)}, status=404)



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



    parser_classes = [MultiPartParser, FormParser]
    def import_csv(self, request, event_id=None, *args, **kwargs):

        if not event_id:
            return Response({"detail": "event_id missing in path"}, status=400)

        f = request.FILES.get("file") or request.data.get("file")
        if not f:
            return Response({"detail": "file is required"}, status=400)

        try:
            raw = f.read()
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
            reader = csv.DictReader(io.StringIO(text))
        except Exception as e:
            return Response({"detail": f"invalid CSV: {e}"}, status=400)

        imported, skipped = 0, []
        for idx, row in enumerate(reader, start=2):
            name  = (row.get("name")  or "").strip()
            email = (row.get("email") or "").strip().lower()
            if not name or not email:
                skipped.append({"line": idx, "reason": "missing name or email"})
                continue
            payload = {
                "eventId": event_id,
                "name": name,
                "email": email,
                "phone": (row.get("phone") or "").strip(),
                "dietaryRestriction": (row.get("dietary_restriction") or "").strip(),
                "accessibilityNeeds": (row.get("accessibility_needs") or "").strip(),
            }
            upsert_guest(event_id, payload)
            imported += 1

        return Response({"imported": imported, "skipped": skipped}, status=201)
    

    def qr(self, request, event_id=None, pk=None):
    # list_guests returns (items, next_page_token) or just items
        res = list_guests(event_id=event_id, limit=5000)

        guests = res[0] if isinstance(res, tuple) else res
        if not isinstance(guests, list):
            return Response({"detail": "Unexpected repository shape"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Find the guest by id
        target = None
        for x in guests:
            gid = str(x.get("id") or x.get("uid") or x.get("guest_id") or "")
            if gid == str(pk):
                target = x
                break

        if not target:
            return Response({"detail": "Guest not found."}, status=status.HTTP_404_NOT_FOUND)

        token = encrypt_payload({"e": str(event_id), "g": str(pk)})
    
        png = qr_png_bytes(token)
        filename = f"guest-{slugify(target.get('name') or pk)}.png"
        resp = HttpResponse(png, content_type="image/png")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp