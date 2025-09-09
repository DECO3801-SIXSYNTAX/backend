# accounts/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Import here (after apps are ready) to avoid circular imports
        from .firebase_sync import (
            upsert_user_in_auth_and_firestore,
            delete_user_in_auth_and_firestore,
        )

        User = get_user_model()

        def _on_saved(sender, instance, **kwargs):
            # Sync on create + update
            try:
                upsert_user_in_auth_and_firestore(instance)
            except Exception as e:
                # Log and continue; don't break admin/requests
                import logging
                logging.getLogger(__name__).exception(
                    "Firebase post_save sync failed for %s: %s", instance.email, e
                )

        def _on_deleted(sender, instance, **kwargs):
            try:
                delete_user_in_auth_and_firestore(instance)
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(
                    "Firebase post_delete sync failed for %s: %s", instance.email, e
                )

        post_save.connect(
            _on_saved, sender=User, dispatch_uid="accounts_user_saved_firebase"
        )
        post_delete.connect(
            _on_deleted, sender=User, dispatch_uid="accounts_user_deleted_firebase"
        )
