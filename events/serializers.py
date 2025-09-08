from rest_framework import serializers
from .models import Event, Guest
class EventSerializer(serializers.ModelSerializer):
    class Meta: model = Event; fields='__all__'
class GuestSerializer(serializers.ModelSerializer):
    class Meta: model = Guest; fields='__all__'
