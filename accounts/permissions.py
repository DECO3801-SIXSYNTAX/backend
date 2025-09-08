
from rest_framework import permissions

class IsPlannerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(user, 'role', None) in ('PLANNER', 'ADMIN')
