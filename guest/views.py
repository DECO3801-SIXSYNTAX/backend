# guests/views.py
from authentication.permissions import IsPlanner
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, MultiPartParser, JSONParser
from .emails import send_guest_qr_email
import csv, io
from django.http import HttpResponse

from .serializers import GuestSerializer
from .repository import get_guest, upsert_guest, delete_guest, list_guests, toggle_checkin, get_event, resolve_guest_email_from_event, partial_update_guest
from typing import List, Optional, Any, Dict
from datetime import datetime
from crypto.qr import encrypt_payload, qr_png_bytes, decrypt_payload, decrypt_to_guest
from django.conf import settings
from django.utils.text import slugify

from urllib.parse import urlparse, parse_qs

def _format_dt(ts, tz=None):
        """Format Firestore Timestamp or ISO/datetime to 'DD Mon YYYY' and 'H:MM AM/PM'."""
        if not ts:
            return "", ""
        # Firestore Timestamp has .to_datetime()
        if hasattr(ts, "to_datetime"):
            dt = ts.to_datetime()
        else:
            if isinstance(ts, str):
                try:
                    # you imported `datetime` (class) above
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    # fallback: leave date as-is, no time
                    return str(ts), ""
            else:
                dt = ts
        # NOTE: if you store a timezone string, localize here
        date_s = dt.strftime("%d %b %Y")
        # %-I works on Unix; on Windows use %#I. If you need portability, use two branches.
        time_s = dt.strftime("%-I:%M %p") if hasattr(dt, "strftime") else ""
        return date_s, time_s


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

@api_view(["POST"])
def bulk_send_invites(request, event_id: str):
    base_url = request.data.get("baseUrl") or "https://app.example.com"
    guest_ids: Optional[List[str]] = request.data.get("guestIds") or None
    if guest_ids:
        guest_ids = [str(g).strip() for g in guest_ids if str(g).strip()]

    
    event = get_event(event_id)
    if not event:
        return Response({"detail": "Event not found"}, status=404)

    items, _ = list_guests(event_id=event_id, limit=5000)
    targets = [(str(g.get("id")), g) for g in items]

    event_name = event.get("name") or event.get("title") or "Your Event"
    starts_at  = event.get("startsAt")
    venue_name = event.get("venueName", "")
    venue_addr = event.get("venueAddress", "")
    org_name   = event.get("orgName", "Event Team")
    org_reply  = event.get("orgReplyEmail", "no-reply@example.com")
    event_date, event_time = _format_dt(starts_at)

    sent, skipped = [], []
    for gid, guest in targets:
        try:
            if not guest:
                skipped.append({"guestId": gid, "reason": "not_found"})
                continue

            email = resolve_guest_email_from_event(event, gid) or (guest.get("email") or "").strip().lower()
            if not email:
                skipped.append({"guestId": gid, "reason": "missing_email"})
                continue

            send_guest_qr_email(
                event_id=str(event_id),
                guest_id=str(gid),                   
                guest_email=email,
                guest_name=guest.get("name", ""),
                base_url=base_url,
                event_name=event_name,
                event_date=event_date,
                event_time=event_time,
                venue_name=venue_name,
                venue_address=venue_addr,
                org_name=org_name,
                org_reply_email=org_reply,
            )
            sent.append(gid)
        except Exception as e:
            skipped.append({"guestId": gid, "reason": str(e)})

    return Response({
        "ok": True,
        "eventId": str(event_id),
        "requested": len(guest_ids) if guest_ids else "all",
        "sent": sent,
        "skipped": skipped,
        "counts": {"sent": len(sent), "skipped": len(skipped)},
    })


class GuestFirebaseViewSet(viewsets.ViewSet):
    """
    /api/guests (GET, POST)
    /api/guests/{id} (PATCH, DELETE)
    /api/guests/toggle-checkin (POST)
    /api/guests/import-csv (POST multipart)
    """

    permission_classes = [IsAuthenticated, IsPlanner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request, event_id=None):
        q        = request.query_params.get("q")
        tags_any = request.query_params.getlist("tags") or None
        limit    = int(request.query_params.get("limit", 50))
        page_tok = request.query_params.get("pageToken")

        items, next_token = list_guests(event_id, q=q, tags_any=tags_any, limit=limit, page_token=page_tok)
        return Response({"items": items, "nextPageToken": next_token})

    def create(self, request, event_id=None):
        data = {**request.data, "eventId": event_id}   
        data.pop("seat", None)                          
        ser = GuestSerializer(data=data)
        ser.is_valid(raise_exception=True)
        gid = upsert_guest(event_id, ser.validated_data)
        return Response({"id": gid}, status=201)

    def partial_update(self, request, pk=None, event_id=None):
        data = {**request.data}
        ser = GuestSerializer(data=data, partial=True)
        ser.is_valid(raise_exception=True)
        gid = partial_update_guest(event_id, pk, ser.validated_data, actor=request.user)
        return Response({"id": gid})

    def destroy(self, request, pk=None, event_id=None):
        delete_guest(event_id, pk)
        return Response(status=204)

    
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
    