from django.contrib import admin
from .models import Event, Guest
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display=('name','date','venue','status','owner')
    list_filter=('status','date')
    search_fields=('name','venue')
@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display=('name','email','phone','event')
    search_fields=('name','email','phone')
    list_filter=('event',)
