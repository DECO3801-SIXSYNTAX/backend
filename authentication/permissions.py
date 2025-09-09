# authentication/permissions.py
from rest_framework.permissions import BasePermission

class RoleRequired(BasePermission):
    needed = []

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in self.needed)

class IsAdmin(RoleRequired):   needed = ["admin"]
class IsPlanner(RoleRequired): needed = ["planner"]
class IsVendor(RoleRequired):  needed = ["vendor"]
class IsGuest(RoleRequired):   needed = ["guest"]
