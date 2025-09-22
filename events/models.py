from django.db import models
from django.conf import settings
import uuid
class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT","Draft"
        PUBLISHED = "PUBLISHED","Published"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_events')
    def __str__(self): return self.name
class Guest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='guests')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.name} - {self.event.name}"
