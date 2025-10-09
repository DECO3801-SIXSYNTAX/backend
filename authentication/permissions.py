# authentication/permissions.py
from rest_framework.permissions import BasePermission
from event import repository as erepo

class RoleRequired(BasePermission):
    needed = []

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in self.needed)

class IsAdmin(RoleRequired):   needed = ["admin"]

class IsPlanner(BasePermission):
    """
    Ethical intent:
    - Contextual access control: hanya planner yang memiliki tanggung jawab pada event ini
      yang boleh membaca/mengubah resource (privacy & accountability).
    """
    def has_permission(self, request, view):
        event_id = view.kwargs.get("event_id") or request.data.get("event_id") or request.query_params.get("event_id")
        if not event_id or not request.user or not request.user.is_authenticated:
            return False
        ev = erepo.get_event(event_id)
        if not ev:
            return False
        uid = str(getattr(request.user, "id", ""))
        return uid == str(ev.get("createdBy")) or uid in map(str, (ev.get("collaborators") or []))
    
class IsVendor(RoleRequired):  needed = ["vendor"]
class IsGuest(RoleRequired):   needed = ["guest"]
