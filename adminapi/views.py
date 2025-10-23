from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from authentication.models import User
from authentication.serializers import UserSerializer

from events.models import Event
from event.serializers import EventSerializer

from .permissions import IsAdminOnly, IsPlannerOrAdmin
from .serializers import AdminUserUpdateSerializer, AdminEventUpdateSerializer, ActivitySerializer
from .models import AdminSettings
from .activity import log_activity

from datetime import datetime, timezone

from SiPanit.firebase import get_db
from firebase_admin import firestore

FIRESTORE_COLLECTION_EVENTS = "events"
FIRESTORE_COLLECTION_USERS = "users"

def _ts_to_iso(ts):
    """Firestore DatetimeWithNanoseconds or datetime -> ISO 8601 (UTC)."""
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):  # datetime or DatetimeWithNanoseconds
        dt = ts
    else:
        to_dt = getattr(ts, "to_datetime", None)
        dt = to_dt() if callable(to_dt) else None
    if dt is None:
        return str(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()

def _event_doc_to_dict(doc):
    """Convert Firestore doc -> dict that matches EventSerializer fields."""
    d = doc.to_dict() or {}
    d["id"] = doc.id

    # Normalize timestamp-like fields if present
    for key in ("createdAt", "updatedAt", "startDate", "endDate"):
        if key in d and d[key] is not None:
            d[key] = _ts_to_iso(d[key])

    # Ensure optional list fields exist as lists
    for key in ("tags", "collaborators"):
        if key in d and d[key] is None:
            d[key] = []
    return d

def _case_insensitive_contains(s, q):
    return q in (s or "").lower()

def _coerce_status(val):
    """Accept True/False or 'active'/'suspended' strings → bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("active", "true", "1", "yes"):
            return True
        if v in ("suspended", "false", "0", "no"):
            return False
    return None  # invalid/unknown

def _ci_contains(s: str, q: str) -> bool:
    return q in (s or "").lower()

def _user_to_light(d: dict) -> dict:
    is_active = bool(d.get("is_active", True))
    return {
        "username": d.get("username", "") or "",
        "email":  d.get("email", "") or "",
        "role":       d.get("role", "") or "",
        "status":     "active" if is_active else "suspended",
    }



class AdminUsersViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def list(self, request):
        """
        GET /api/admin/users/?role=ADMIN&status=active&q=aryaf&limit=50
        Returns only: first_name, last_name, role, status
        """
        db = get_db()
        ref = db.collection(FIRESTORE_COLLECTION_USERS)

        try:
            ref = ref.order_by("username")
        except Exception:
            try:
                ref = ref.order_by("email")
            except Exception:
                pass

        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100

        q = (request.query_params.get("q") or "").strip().lower()
        fetch_limit = limit if not q else min(max(limit * 3, 100), 500)

        snaps = list(ref.limit(fetch_limit).stream())

        rows = []
        if q:
            for s in snaps:
                d = s.to_dict() or {}
                if (
                    _ci_contains(d.get("username", ""), q)
                    or _ci_contains(d.get("email", ""), q)
                    or _ci_contains(d.get("first_name", ""), q)
                    or _ci_contains(d.get("last_name", ""), q)
                ):
                    rows.append({**_user_to_light(d), "id": s.id})   # <-- include id
        else:
            rows = [{**_user_to_light(s.to_dict() or {}), "id": s.id} for s in snaps]  # <-- include id

        rows = rows[:limit]
        return Response(rows)
        
    def partial_update(self, request, pk=None):
        """
        PATCH /api/admin/users/{id}
        Body can include: { first_name, last_name, role, status }
        - 'status': "active"/"suspended" -> is_active True/False
        """
        if not pk:
            return Response({"detail": "Missing id"}, status=400)

        db = get_db()
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(pk)
        snap = doc_ref.get()
        if not snap.exists:
            return Response({"detail": "Not found"}, status=404)

        ser = AdminUserUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        updates = {}

        if "first_name" in data:
            updates["first_name"] = (data["first_name"] or "").strip()
        if "last_name" in data:
            updates["last_name"] = (data["last_name"] or "").strip()

        if "role" in data and data["role"]:
            # keep snake_case / lowercase in Firestore
            updates["role"] = str(data["role"]).strip().lower()

        if "status" in data:
            new_active = _coerce_status(data["status"])
            if new_active is None:
                return Response({"status": ["Invalid status"]}, status=400)
            updates["is_active"] = new_active

        if updates:
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            doc_ref.update(updates)

            log_activity(
                action="user.update",
                entity_type="user",
                entity_id=str(pk),
                event_id=None,
                actor_id=str(getattr(request.user, "id", "")),
                actor_email=getattr(request.user, "email", None),
            )

        # return a lightweight, consistent shape
        snap = doc_ref.get()
        d = snap.to_dict() or {}
        payload = {
            "id": pk,
            "username": d.get("username", "") or "",
            "email": d.get("email", "") or "",
            "role": d.get("role", "") or "",
            "status": "active" if d.get("is_active", True) else "suspended",
            "first_name": d.get("first_name", "") or "",
            "last_name": d.get("last_name", "") or "",
        }
        return Response(payload)


class AdminEventsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def list(self, request):
        """
        GET /api/admin/events/?status=active&q=Tech&limit=100

        Firestore rules:
        - We try to filter by status server-side.
        - `q` (search on name/venue) is done client-side (contains/ci).
        """
        db = get_db()
        ref = db.collection(FIRESTORE_COLLECTION_EVENTS)

        status_param = (request.query_params.get("status") or "").strip()
        if status_param:
            ref = ref.where("status", "==", status_param)

        # Order by name if possible; some compound queries need an index.
        try:
            ref = ref.order_by("name")
        except Exception:
            # Fallback: skip order_by if index missing
            pass

        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100

        # Fetch a bit more if we need to do client-side search
        q = (request.query_params.get("q") or "").strip().lower()
        fetch_limit = limit if not q else min(max(limit * 3, 100), 500)

        snaps = list(ref.limit(fetch_limit).stream())
        rows = [_event_doc_to_dict(s) for s in snaps]

        if q:
            rows = [r for r in rows if _case_insensitive_contains(r.get("name", ""), q)
                                     or _case_insensitive_contains(r.get("venue", ""), q)]
        rows = rows[:limit]

        return Response(EventSerializer(rows, many=True).data)
    
    def partial_update(self, request, pk=None):
        """
        PATCH /api/admin/events/{id}
        Body: { "status": "<new_status>" }
        Only 'status' is updatable here.
        """
        if not pk:
            return Response({"detail": "Missing id"}, status=400)

        db = get_db()
        doc_ref = db.collection(FIRESTORE_COLLECTION_EVENTS).document(pk)
        snap = doc_ref.get()
        if not snap.exists:
            return Response({"detail": "Not found"}, status=404)

        # Require 'status' and only update that field
        if "status" not in request.data:
            return Response({"status": ["This field is required."]}, status=400)

        raw_status = request.data.get("status")
        new_status = str(raw_status).strip() if raw_status is not None else ""
        if not new_status:
            return Response({"status": ["Invalid status"]}, status=400)

        # Update only status (+ updatedAt)
        doc_ref.update({
            "status": new_status,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        # Read back and respond
        snap = doc_ref.get()
        payload = _event_doc_to_dict(snap)

        log_activity(
            action="event.status.update",
            entity_type="event",
            entity_id=str(pk),
            event_id=str(pk),
            actor_id=str(getattr(request.user, "id", "")),
            actor_email=getattr(request.user, "email", None),
        )
        return Response(EventSerializer(payload).data)


    def destroy(self, request, pk=None):
        if not pk:
            return Response({"detail": "Missing id"}, status=400)

        db = get_db()
        doc_ref = db.collection(FIRESTORE_COLLECTION_EVENTS).document(pk)
        snap = doc_ref.get()
        if not snap.exists:
            return Response({"detail": "Not found"}, status=404)

        doc_ref.delete()

        log_activity(
            action="event.delete",
            entity_type="event",
            entity_id=str(pk),
            event_id=str(pk),
            actor_id=str(getattr(request.user, "id", "")),
            actor_email=getattr(request.user, "email", None),
        )
        return Response(status=204)


class RecentActivityView(APIView):
    permission_classes = [IsPlannerOrAdmin]

    def get(self, request):
        event_id = request.query_params.get("eventId")
        limit = int(request.query_params.get("limit", 30))

        db = get_db()
        ref = db.collection("activity")
        if event_id:
            ref = ref.where("eventId", "==", event_id)
        ref = ref.order_by("ts", direction="DESCENDING").limit(limit)

        snaps = list(ref.stream())
        items = []
        for s in snaps:
            d = s.to_dict() or {}
            ts = d.get("ts")
            if ts:
                if isinstance(ts, datetime):
                    # Firestore DatetimeWithNanoseconds is a datetime subclass.
                    # Normalize to ISO 8601 (UTC).
                    if ts.tzinfo is None:
                        d["ts"] = ts.replace(tzinfo=timezone.utc).isoformat()
                    else:
                        d["ts"] = ts.astimezone(timezone.utc).isoformat()
                else:
                    # Fallbacks: Timestamp-like objects with to_datetime(), or just str()
                    to_dt = getattr(ts, "to_datetime", None)
                    if callable(to_dt):
                        dt = to_dt()
                        d["ts"] = (
                            dt.replace(tzinfo=timezone.utc).isoformat()
                            if dt.tzinfo is None else dt.astimezone(timezone.utc).isoformat()
                        )
                    else:
                        d["ts"] = str(ts)
            d["id"] = s.id
            items.append(d)

        ser = ActivitySerializer(items, many=True)
        return Response({"items": ser.data})