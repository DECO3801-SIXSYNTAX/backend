# guests/serializers.py
from rest_framework import serializers

class GuestSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    eventId = serializers.CharField()
    name  = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dietaryRestriction = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    accessibilityNeeds = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    seat = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
