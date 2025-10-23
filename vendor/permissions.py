from rest_framework.permissions import BasePermission

class IsVendor(BasePermission):
    """Permission untuk role vendor"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            getattr(request.user, 'role', '') == 'vendor'
        )