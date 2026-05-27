from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'action', 'performed_by', 'performed_at', 'activity', 'source_file']
    list_filter = ['action', 'performed_at']
    search_fields = ['note', 'activity__id', 'source_file__original_filename']
    readonly_fields = ['activity', 'source_file', 'action', 'performed_by', 'performed_at', 'field_changed', 'old_value', 'new_value', 'note']
    ordering = ['-performed_at']

    def has_add_permission(self, request):
        # Audit logs should only be created programmatically
        return False

    def has_change_permission(self, request, obj=None):
        # Audit logs are immutable
        return False

    def has_delete_permission(self, request, obj=None):
        # Audit logs are never deleted
        return False
