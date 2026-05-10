# audits/admin.py
from django.contrib import admin

from apps.audits.models import BusinessEvent


@admin.register(BusinessEvent)
class BusinessEventAdmin(admin.ModelAdmin):
    list_display = ["action", "user", "ip_address", "request_id", "created_at"]
    list_filter = ["action"]
    search_fields = ["action", "user__email", "request_id"]
    readonly_fields = [
        "action",
        "user",
        "metadata",
        "ip_address",
        "request_id",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
