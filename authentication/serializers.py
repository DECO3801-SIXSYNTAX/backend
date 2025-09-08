from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()

class AssignRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["Admin", "Planner", "Vendor", "Guest"])

class UserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "is_active", "is_staff", "is_superuser", "roles")

    def get_roles(self, obj):
        return list(obj.groups.values_list("name", flat=True))