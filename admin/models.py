from django.db import models

class AdminSettings(models.Model):
    id   = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    data = models.JSONField(default=dict, blank=True)

    @classmethod
    def get(cls) -> "AdminSettings":
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"data": {}})
        return obj
