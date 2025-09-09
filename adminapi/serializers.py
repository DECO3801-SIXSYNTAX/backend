from rest_framework import serializers

ROLE_CHOICES = ["ADMIN", "PLANNER", "VENDOR", "GUEST"]

class AdminUserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name  = serializers.CharField(required=False, allow_blank=True)
    role       = serializers.ChoiceField(choices=ROLE_CHOICES, required=False)
    status     = serializers.ChoiceField(choices=["active", "suspended"], required=False)

class AdminEventUpdateSerializer(serializers.Serializer):
    name   = serializers.CharField(required=False)
    date   = serializers.DateField(required=False)
    venue  = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=["draft", "planning", "active"], required=False)