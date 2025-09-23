from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsPlanner
from .serializers import EventSerializer
from . import repository as repo

def _can_access(user, event_dict) -> bool:
    return str(event_dict.get("createdBy")) == str(user.id) or user.is_superuser

class EventViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPlanner]

    def list(self, request):
        mine = request.query_params.get("mine")
        owner_id = str(request.user.id) if mine == "1" else None
        return Response(repo.list_events(owner_id))

    def retrieve(self, request, pk=None):
        item = repo.get_event(pk)
        if not item:
            return Response({"detail": "Not found"}, status=404)
        if not _can_access(request.user, item):
            return Response({"detail": "Forbidden"}, status=403)
        return Response(item)

    def create(self, request):
        data = dict(request.data)
        data["createdBy"] = str(request.user.id)
        ser = EventSerializer(data=data); ser.is_valid(raise_exception=True)
        eid = repo.upsert_event(ser.validated_data)
        return Response({"id": eid}, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        current = repo.get_event(pk)
        if not current:
            return Response({"detail": "Not found"}, status=404)
        if not _can_access(request.user, current):
            return Response({"detail": "Forbidden"}, status=403)

        data = dict(request.data); data["id"] = pk
        data["createdBy"] = current.get("createdBy")
        ser = EventSerializer(data=data); ser.is_valid(raise_exception=True)
        eid = repo.upsert_event(ser.validated_data)
        return Response({"id": eid})

    def destroy(self, request, pk=None):
        current = repo.get_event(pk)
        if not current:
            return Response(status=204)
        if not _can_access(request.user, current):
            return Response({"detail": "Forbidden"}, status=403)
        repo.delete_event(pk)
        return Response(status=204)
