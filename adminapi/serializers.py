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

class ActivitySerializer(serializers.Serializer):
    id = serializers.CharField()
    ts = serializers.DateTimeField()
    action = serializers.CharField()
    entityType = serializers.CharField()
    entityId = serializers.CharField()
    eventId = serializers.CharField(allow_null=True, required=False)
    actorId = serializers.CharField(allow_null=True, required=False)
    actorEmail = serializers.EmailField(allow_null=True, required=False)
    
    # Optional human-readable sentence
    summary = serializers.SerializerMethodField()

    def get_summary(self, obj):
        action = obj.get("action")
        actor = obj.get("actorEmail") or "someone"
        d = obj.get("details") or {}
        name = d.get("name")
        email = d.get("email")
        seat = d.get("seat")
        checked = d.get("checkedIn")
        title = d.get("title")
        enabled = d.get("checkInEnabled")
        who = name or email or obj.get("entityId")

        if action == "guest.create":
            return f"{actor} added guest {who}."
        if action == "guest.update":
            if seat: return f"{actor} updated {who}'s seat to {seat}."
            return f"{actor} updated guest {who}."
        if action == "guest.delete":
            return f"{actor} deleted guest {who}."
        if action == "guest.checkin.toggle":
            state = "checked in" if checked else "unchecked"
            return f"{actor} {state} {who}."
        if action == "event.upsert":
            parts = []
            if title: parts.append(f'title to "{title}"')
            if enabled is not None: parts.append(f"check-in {'enabled' if enabled else 'disabled'}")
            change = " and ".join(parts) if parts else "event details"
            return f"{actor} updated event {obj.get('eventId')} ({change})."
        return f"{actor} performed {action} on {obj.get('entityType')} {obj.get('entityId')}."
