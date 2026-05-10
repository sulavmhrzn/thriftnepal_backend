from django.db import models

from apps.core.models import BaseModel


class BusinessEvent(BaseModel):
    """Logs non-model business events"""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, null=True, blank=True
    )
    action = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    request_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"
