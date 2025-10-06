from rest_framework.permissions import BasePermission


class IsAdminOnly(BasePermission):
    """
    Allow only Django users whose role is ADMIN.
    Works with your existing SimpleJWT auth (request.user is accounts.User).
    """
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and getattr(u, "is_authenticated", False) and (getattr(u, "role", "") == "admin"))