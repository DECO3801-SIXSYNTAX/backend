from rest_framework import permissions
class IsPlannerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u,'role',None) in ('PLANNER','ADMIN'))
