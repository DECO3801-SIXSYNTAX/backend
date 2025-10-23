from rest_framework import serializers

class VendorEventListSerializer(serializers.Serializer):
    """Serializer untuk list events (card view)"""
    id = serializers.CharField()
    name = serializers.CharField()
    date = serializers.CharField(source='startDate', allow_null=True)
    venue = serializers.CharField(allow_null=True, allow_blank=True)
    status = serializers.CharField()
    attendees = serializers.IntegerField(source='expectedAttendees', default=0)
    capacity = serializers.IntegerField(default=0)

class VendorEventDetailSerializer(serializers.Serializer):
    """Serializer untuk detail event"""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True, allow_blank=True)
    type = serializers.CharField(allow_null=True, allow_blank=True)
    startDate = serializers.CharField()
    endDate = serializers.CharField()
    venue = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)
    capacity = serializers.IntegerField(default=0)
    expectedAttendees = serializers.IntegerField(default=0)
    actualAttendees = serializers.IntegerField(default=0)
    budget = serializers.FloatField(default=0)
    status = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    createdBy = serializers.CharField()
    createdAt = serializers.CharField(allow_null=True)
    updatedAt = serializers.CharField(allow_null=True)