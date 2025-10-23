from rest_framework import viewsets, permissions
from .models import Event, Guest
from .serializers import EventSerializer, GuestSerializer
from accounts.permissions import IsPlannerOrAdmin
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS: return True
        return getattr(obj,'owner_id',None) == request.user.id
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly & IsPlannerOrAdmin]
    def perform_create(self, serializer): serializer.save(owner=self.request.user)
class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAuthenticated]
