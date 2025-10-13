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

FIRESTORE_COLLECTION_EVENTS = "events"

def _ts_to_iso(ts):
    """Firestore DatetimeWithNanoseconds or datetime -> ISO 8601 (UTC)."""
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
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

    # normalize timestamp-like fields if present
    for key in ("createdAt", "updatedAt", "startDate", "endDate"):
        if key in d and d[key] is not None:
            d[key] = _ts_to_iso(d[key])

    # optional list
    for key in ("tags", "collaborators"):
        if key in d and d[key] is None:
            d[key] = []
    return d


def _case_insensitive_contains(s, q):
    return q in (s or "").lower()



class AdminUsersViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def list(self, request):
        """
        GET /api/admin/users/
        """
        qs = User.objects.all().order_by("-last_login", "username")

        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role.upper())

        status_param = (request.query_params.get("status") or "").strip().lower()
        if status_param in ("active", "true"):
            qs = qs.filter(is_active=True)
        elif status_param in ("suspended", "false"):
            qs = qs.filter(is_active=False)

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )

        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100

        users = list(qs[:limit])
        return Response(UserSerializer(users, many=True).data)

    

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