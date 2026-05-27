import hashlib
from django.db import models
from apps.core.models import Organization, User


class SourceFile(models.Model):
    """
    Tracks uploaded CSV files and ingestion metadata.
    Duplicate detection via file_hash (SHA256).
    """
    SOURCE_TYPE_CHOICES = [
        ('SAP', 'SAP MB51'),
        ('UTILITY', 'Utility Bill'),
        ('TRAVEL_CONCUR', 'Concur Travel'),
        ('TRAVEL_NAVAN', 'Navan Travel'),
    ]

    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='source_files')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash for duplicate detection"
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    total_rows = models.IntegerField(null=True, blank=True)
    failed_rows = models.IntegerField(null=True, blank=True, default=0)
    flagged_rows = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = 'source_files'
        unique_together = ['org', 'file_hash']
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.get_source_type_display()}) - {self.get_status_display()}"

    @staticmethod
    def compute_hash(file_content):
        """
        Compute SHA256 hash of file content.

        Args:
            file_content: bytes or file-like object

        Returns:
            str: SHA256 hash as hexadecimal string
        """
        if isinstance(file_content, bytes):
            return hashlib.sha256(file_content).hexdigest()
        else:
            # File-like object
            hasher = hashlib.sha256()
            for chunk in iter(lambda: file_content.read(4096), b''):
                hasher.update(chunk)
            file_content.seek(0)  # Reset file pointer
            return hasher.hexdigest()


class RawRecord(models.Model):
    """
    Immutable snapshot of original CSV row.
    NEVER edited, NEVER deleted (except cascade when SourceFile deleted).
    """
    PARSE_STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('EXCLUDED', 'Excluded'),
    ]

    source_file = models.ForeignKey(
        SourceFile,
        on_delete=models.CASCADE,
        related_name='raw_records'
    )
    row_number = models.IntegerField(help_text="1-indexed row number from CSV")
    raw_data = models.JSONField(help_text="Original CSV row as dict with header keys")
    ingested_at = models.DateTimeField(auto_now_add=True)
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='SUCCESS')
    parse_error = models.TextField(null=True, blank=True)
    exclude_reason = models.TextField(
        null=True,
        blank=True,
        help_text="e.g., 'BWART=122 returns excluded'"
    )

    class Meta:
        db_table = 'raw_records'
        ordering = ['source_file', 'row_number']
        indexes = [
            models.Index(fields=['source_file', 'row_number']),
        ]

    def __str__(self):
        return f"{self.source_file.original_filename} - Row {self.row_number} ({self.get_parse_status_display()})"
