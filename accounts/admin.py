from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # show role/email in list
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")

    # add our role to the standard fieldsets
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("App info", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("App info", {"fields": ("role",)}),
    )

    # make email required in forms
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["email"].required = True
        return form

    # optional: add a bulk action to push users to Firebase
    actions = ["sync_to_firebase"]

    def sync_to_firebase(self, request, queryset):
        from .firebase_sync import sync_user_to_firebase
        ok, fail = 0, 0
        for u in queryset:
            if not u.email:
                fail += 1
                continue
            try:
                sync_user_to_firebase(u)
                ok += 1
            except Exception:
                fail += 1
        self.message_user(request, f"Synced {ok} users, {fail} failed.")
    sync_to_firebase.short_description = "Sync selected users to Firebase"
