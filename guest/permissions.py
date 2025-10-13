# authentication/permissions.py
from rest_framework.permissions import BasePermission

class RoleRequired(BasePermission):
    needed = []

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in self.needed)

class IsPlannerorAdmin(RoleRequired):   needed = ["planner", "admin"]
