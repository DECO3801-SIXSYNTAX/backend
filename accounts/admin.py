from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User
from .firebase_sync import upsert_user_in_auth_and_firestore


class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    list_display = ("username", "email", "first_name", "last_name", "role")
    list_filter = ("role", "is_staff", "is_superuser")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone", "company")}),
        ("Professional info", {"fields": ("experience", "specialty")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "role"),
            },
        ),
    )
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            uid = upsert_user_in_auth_and_firestore(obj)
            self.message_user(request, f"[Firebase Sync] Synced user to Firebase UID {uid}")
        except Exception as e:
            self.message_user(request, f"[Firebase Sync ERROR] {e}", level="error")


admin.site.register(User, UserAdmin)
