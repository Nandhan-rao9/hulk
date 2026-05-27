from django.db import models
from apps.core.models import User


class AuditLog(models.Model):
    """
    Append-only log of all state changes.
    Never deleted - persists even if related activity/file deleted.
    """
    ACTION_CHOICES = [
        ('INGESTED', 'Ingested'),
        ('REVIEWED', 'Reviewed'),
        ('EDITED', 'Edited'),
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged'),
        ('LOCKED', 'Locked'),
        ('UNLOCKED', 'Unlocked'),
        ('EDIT_REJECTED', 'Edit Rejected'),
        ('MANUAL_CLASSIFICATION', 'Manual Classification'),
        ('PERIOD_LOCKED', 'Period Locked'),
        ('LATE_ARRIVAL', 'Late Arrival'),
        ('FILE_INVALIDATED', 'File Invalidated'),
    ]

    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True,
        help_text="Null if activity deleted - log persists"
    )
    source_file = models.ForeignKey(
        'ingestion.SourceFile',
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True,
        help_text="Null if source file deleted - log persists"
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='audit_actions',
        null=True,
        blank=True,
        help_text="Null for system actions"
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    field_changed = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['activity']),
            models.Index(fields=['performed_at']),
        ]

    def __str__(self):
        actor = self.performed_by.username if self.performed_by else 'System'
        return f"{self.get_action_display()} by {actor} at {self.performed_at.strftime('%Y-%m-%d %H:%M')}"
