from rest_framework.permissions import BasePermission, SAFE_METHODS

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or user_in_group(request.user, "Admin")
        )

class IsPlannerRole(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "Planner")

class IsVendorRole(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "Vendor")

class IsGuestRole(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "Guest")