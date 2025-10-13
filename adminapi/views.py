from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from authentication.models import User
from authentication.serializers import UserSerializer

from events.models import Event
from events.serializers import EventSerializer

from .permissions import IsAdminOnly, IsPlannerOrAdmin
from .serializers import AdminUserUpdateSerializer, AdminEventUpdateSerializer, ActivitySerializer
from .models import AdminSettings
from .activity import log_activity

from SiPanit.firebase import get_db


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

        status_param = request.query_params.get("status")
        if status_param == "active":
            qs = qs.filter(is_active=True)
        elif status_param == "suspended":
            qs = qs.filter(is_active=False)

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))

        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100

        users = list(qs[:limit])
        return Response(UserSerializer(users, many=True).data)

    def partial_update(self, request, pk=None):
        """
        PATCH body can include: { first_name, last_name, role, status }
        'status' -> is_active (active=True, suspended=False)
        """
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        ser = AdminUserUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        changed = False
        if "role" in data and data["role"]:
            u.role = data["role"]; changed = True
        if "status" in data:
            u.is_active = data["status"]; changed = True

        if changed:
            u.save(update_fields=["role","is_active"])
            log_activity(
            action="user.update",
            entity_type="user",
            entity_id=str(u.id),
            event_id=None,
            actor_id=str(request.user.id),
            actor_email=request.user.email,
        )

        return Response(UserSerializer(u).data)


class AdminEventsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def list(self, request):
        """
        GET /api/admin/events/?status=active&q=Tech&limit=100
        """
        qs = Event.objects.all().order_by("name")

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(venue__icontains=q))

        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100

        events = list(qs[:limit])
        return Response(EventSerializer(events, many=True).data)


    def partial_update(self, request, pk=None):
        """
        PATCH body can include: { name, date, venue, status }
        """
        try:
            ev = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        ser = AdminEventUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if "status" in data:
            ev.status = (data["status"]); changed = True

        if changed:
            ev.save(update_fields=["status"])
            log_activity(
                action="event.update",           # or "event.update" if you prefer
                entity_type="event",
                entity_id=str(ev.id),
                event_id=str(ev.id),
                actor_id=str(getattr(request.user, "id", "")),
                actor_email=getattr(request.user, "email", None),
                #details=changed_fields,          # your ActivitySerializer will turn this into a nice sentence
            )
        return Response(EventSerializer(ev).data)

    def destroy(self, request, pk=None):
        try:
            ev = Event.objects.get(pk=pk)
            entity_id= str(ev.id)
        except Event.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        ev.delete()
        log_activity(
            action="event.delete",
            entity_type="event",
            entity_id=entity_id,
            event_id=entity_id,
            actor_id=str(getattr(request.user, "id", "")),
            actor_email=getattr(request.user, "email", None),
            #details={"name": ev_name},
        )
        return Response(status=204)

class RecentActivityView(APIView):
    permission_classes = [IsPlannerOrAdmin]   # only admin/planner

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
                d["ts"] = ts.datetime.isoformat()
            d["id"] = s.id
            items.append(d)

        ser = ActivitySerializer(items, many=True)
        return Response({"items": ser.data})