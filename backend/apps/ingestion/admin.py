from django.contrib import admin
from .models import SourceFile, RawRecord


@admin.register(SourceFile)
class SourceFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'source_type', 'org', 'uploaded_by', 'uploaded_at', 'status', 'total_rows', 'flagged_rows']
    list_filter = ['source_type', 'status', 'uploaded_at']
    search_fields = ['original_filename', 'file_hash']
    readonly_fields = ['file_hash', 'uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_file', 'row_number', 'parse_status', 'ingested_at']
    list_filter = ['parse_status', 'ingested_at']
    search_fields = ['source_file__original_filename']
    readonly_fields = ['source_file', 'row_number', 'raw_data', 'ingested_at', 'parse_status', 'parse_error', 'exclude_reason']
    ordering = ['source_file', 'row_number']

    def has_add_permission(self, request):
        # RawRecords should only be created via ingestion process
        return False

    def has_change_permission(self, request, obj=None):
        # Immutable - no editing allowed
        return False

    def has_delete_permission(self, request, obj=None):
        # Immutable - no manual deletion (cascade only)
        return False
