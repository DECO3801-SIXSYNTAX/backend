# accounts/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "ADMIN"

class IsPlanner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "PLANNER"

class IsVendor(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = getattr(request.user, "role", None)
        if role == "VENDOR":
            # vendors can read and create; block PUT/PATCH/DELETE
            return request.method in ["GET", "POST"]
        return False

class IsGuest(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "GUEST"

# ---- Combined / convenience guards ----
class IsPlannerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in {"PLANNER", "ADMIN"}
        )

class IsVendorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = getattr(request.user, "role", None)
        if role == "ADMIN":
            return True
        if role == "VENDOR":
            return request.method in ["GET", "POST"]
        return False

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, "role", None) == "ADMIN"
