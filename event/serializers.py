# event/serializers.py
from rest_framework import serializers

# ---------- Event ----------
class EventSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    startDate = serializers.CharField()
    endDate   = serializers.CharField()
    venue = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    capacity = serializers.IntegerField(required=False)
    expectedAttendees = serializers.IntegerField(required=False)
    actualAttendees   = serializers.IntegerField(required=False)
    budget = serializers.IntegerField(required=False)
    dietaryNeeds = serializers.IntegerField(required=False)
    accessibilityNeeds = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    collaborators = serializers.ListField(child=serializers.CharField(), required=False)
    createdBy = serializers.CharField()
    createdAt = serializers.CharField(required=False)
    updatedAt = serializers.CharField(required=False)

# ---------- Old (versioned) layout ----------
class LayoutElementSer(serializers.Serializer):
    id = serializers.CharField(max_length=120)
    type = serializers.CharField()
    name = serializers.CharField()
    capacity = serializers.IntegerField()
    geom = serializers.DictField()
    assigned_guest_ids = serializers.ListField(child=serializers.CharField(), required=False)

class LayoutSaveSer(serializers.Serializer):
    event_id = serializers.CharField()
    version = serializers.IntegerField()
    canvas = serializers.DictField()
    elements = LayoutElementSer(many=True)
    konva_snapshot = serializers.DictField(required=False, allow_null=True)

# ---------- FE floorplan shape ----------
class FEElementConfigSer(serializers.Serializer):
    id = serializers.CharField()
    shape = serializers.CharField()
    label = serializers.CharField()
    color = serializers.CharField()
    textColor = serializers.CharField()
    defaultWidth = serializers.IntegerField()
    defaultHeight = serializers.IntegerField()
    defaultRadius = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField()

class FEElementSer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField()
    height = serializers.FloatField()
    rotation = serializers.FloatField()
    capacity = serializers.IntegerField()
    name = serializers.CharField()
    assignedGuests = serializers.ListField(child=serializers.CharField())
    config = FEElementConfigSer()
    radius = serializers.FloatField(required=False)

class FERoomBoundarySer(serializers.Serializer):
    vertices = serializers.ListField(child=serializers.DictField(), required=False)
    closed = serializers.BooleanField(required=False)

class FEFloorPlanSer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True)
    eventId = serializers.CharField()
    canvasSize = serializers.DictField()
    pixelsPerMeter = serializers.IntegerField()
    elements = FEElementSer(many=True)
    roomBoundary = FERoomBoundarySer(required=False, allow_null=True)
    createdAt = serializers.CharField(required=False, allow_blank=True)
    updatedAt = serializers.CharField(required=False, allow_blank=True)