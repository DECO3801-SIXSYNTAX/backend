from django.contrib import admin
from rest_framework.authtoken.models import Token

class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'get_roles', 'created')
    search_fields = ('key', 'user__username', 'user__email')

    def get_roles(self, obj):
        return ", ".join(obj.user.groups.values_list("name", flat=True)) or "-"
    get_roles.short_description = "Roles"

try:
    admin.site.unregister(Token)
except admin.sites.NotRegistered:
    pass

admin.site.register(Token, TokenAdmin)
