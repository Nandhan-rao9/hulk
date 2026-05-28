"""
Ingestion service - orchestrates CSV parsing and database writes.

Responsibilities:
- File hash computation and duplicate detection
- SourceFile lifecycle (PROCESSING → DONE/FAILED)
- Transaction boundaries (all-or-nothing)
- RawRecord creation for every CSV row
- Activity + Detail creation via parser
- Suspicious flag application
- Audit log generation
- Statistics tracking (total/failed/flagged rows)

Usage:
    service = IngestionService(file_obj, 'SAP', org, user)
    source_file = service.ingest()
"""
import csv
import io
from typing import Dict
from django.db import transaction
from apps.ingestion.models import SourceFile, RawRecord
from apps.activities.models import Activity
from apps.audit.models import AuditLog


class IngestionService:
    """Orchestrates CSV ingestion for all source types."""

    def __init__(self, file_obj, source_type: str, org, user):
        """
        Initialize ingestion service.

        Args:
            file_obj: File-like object or UploadedFile
            source_type: 'SAP', 'UTILITY', 'TRAVEL_CONCUR', 'TRAVEL_NAVAN'
            org: Organization instance
            user: User instance (uploader)
        """
        self.file_obj = file_obj
        self.source_type = source_type
        self.org = org
        self.user = user
        self.parser = self._get_parser()

    def _get_parser(self):
        """
        Factory method - returns correct parser for source_type.

        Returns:
            BaseParser instance (SAPParser, UtilityParser, or TravelParser)

        Raises:
            ValueError: If source_type is unknown
        """
        from apps.ingestion.parsers.sap_parser import SAPParser
        from apps.ingestion.parsers.utility_parser import UtilityParser
        from apps.ingestion.parsers.travel_parser import TravelParser

        parser_map = {
            'SAP': SAPParser,
            'UTILITY': UtilityParser,
            'TRAVEL_CONCUR': TravelParser,
            'TRAVEL_NAVAN': TravelParser,
        }

        parser_class = parser_map.get(self.source_type)
        if not parser_class:
            raise ValueError(f"Unknown source type: {self.source_type}")

        return parser_class(self.org)

    def ingest(self) -> SourceFile:
        """
        Main ingestion flow.

        Steps:
        1. Compute file hash and check for duplicates
        2. Create SourceFile record with status=PROCESSING
        3. Parse CSV rows and create Activity + Detail records
        4. Update SourceFile with statistics and status=DONE
        5. On error, mark status=FAILED and re-raise

        Returns:
            SourceFile instance with status=DONE

        Raises:
            ValueError: If file is a duplicate
            Exception: Any parsing or database errors
        """
        # Step 1: Duplicate detection (only block if PROCESSING or DONE)
        file_content = self._read_file_content()
        file_hash = SourceFile.compute_hash(file_content)

        existing = SourceFile.objects.filter(
            org=self.org,
            file_hash=file_hash,
            status__in=['PROCESSING', 'DONE']
        ).first()

        if existing:
            raise ValueError(
                f"Duplicate file detected. Already uploaded as '{existing.original_filename}' "
                f"on {existing.uploaded_at.strftime('%Y-%m-%d %H:%M')} with status {existing.status}. "
                f"Delete the existing file first to re-upload."
            )

        # Step 2: Create SourceFile
        source_file = SourceFile.objects.create(
            org=self.org,
            source_type=self.source_type,
            original_filename=self.file_obj.name,
            file_hash=file_hash,
            uploaded_by=self.user,
            status='PROCESSING'
        )

        try:
            # Step 3: Parse and create records (in transaction)
            stats = self._process_rows(source_file, file_content)

            # Step 4: Update source file status
            source_file.status = 'DONE'
            source_file.total_rows = stats['total']
            source_file.failed_rows = stats['failed']
            source_file.flagged_rows = stats['flagged']
            source_file.approved_rows = stats['approved']
            source_file.save()

            return source_file

        except Exception as e:
            # Step 5: Mark as failed and re-raise
            source_file.status = 'FAILED'
            source_file.save()

            # Note: Not logging to AuditLog here - FAILED status is sufficient
            # FILE_INVALIDATED action is for user-initiated invalidation, not parse errors

            raise

    @transaction.atomic
    def _process_rows(self, source_file: SourceFile, file_content: bytes) -> Dict[str, int]:
        """
        Process all CSV rows in a single transaction.

        If any row fails critically, entire transaction rolls back.
        Parse failures (invalid data) are recorded as FAILED RawRecords.

        Args:
            source_file: SourceFile instance
            file_content: Raw file bytes (UTF-8 CSV)

        Returns:
            Dict with keys: total, failed, flagged (row counts)

        Raises:
            Exception: Critical errors (invalid CSV format, missing headers, etc.)
        """
        # Decode file content
        text_content = file_content.decode('utf-8-sig')  # Handles BOM
        csv_reader = csv.DictReader(io.StringIO(text_content))

        # Validate headers
        headers = csv_reader.fieldnames
        if not headers:
            raise ValueError("CSV file is empty or has no headers")

        try:
            self.parser.validate_headers(headers)
        except ValueError as e:
            raise ValueError(f"Invalid CSV headers: {e}")

        # Process rows
        stats = {'total': 0, 'failed': 0, 'flagged': 0, 'approved': 0}
        activities_by_row = {}  # Track activities for post-processing

        for row_num, row_dict in enumerate(csv_reader, start=1):
            stats['total'] += 1

            # Create RawRecord (immutable audit trail)
            raw_record = RawRecord.objects.create(
                source_file=source_file,
                row_number=row_num,
                raw_data=row_dict,
                parse_status='SUCCESS'  # Will update if fails
            )

            # Parse row
            try:
                result = self.parser.parse_row(row_dict, row_num)
            except Exception as e:
                # Parser should not raise, but catch just in case
                result = ParseResult()
                result.mark_failed(f"Parser exception: {str(e)}")

            # Handle parse failures/exclusions
            if result.parse_status != 'SUCCESS':
                raw_record.parse_status = result.parse_status
                raw_record.parse_error = result.parse_error
                raw_record.exclude_reason = result.exclude_reason
                raw_record.save()

                if result.parse_status == 'FAILED':
                    stats['failed'] += 1

                # Don't create Activity for failed/excluded rows
                continue

            # Create Activity
            activity = Activity.objects.create(
                org=self.org,
                source_file=source_file,
                raw_record=raw_record,
                **result.activity_data
            )

            # Track activity for post-processing
            activities_by_row[row_num] = activity

            # Create Detail (SAP/Utility/Travel)
            detail_model = self.parser.get_detail_model()
            detail_model.objects.create(
                activity=activity,
                **result.detail_data
            )

            # Apply suspicious flags (single save for all flags)
            if result.suspicious_flags:
                activity.flag(result.suspicious_flags)  # Pass all flags at once
                stats['flagged'] += 1

                # Log flagging
                AuditLog.objects.create(
                    activity=activity,
                    source_file=source_file,
                    action='FLAGGED',
                    performed_by=None,  # System action
                    note=f"Flagged during ingestion: {', '.join(result.suspicious_flags)}"
                )
            else:
                # Auto-approve clean rows
                activity.status = 'APPROVED'
                activity.save()
                stats['approved'] += 1

                # Log auto-approval
                AuditLog.objects.create(
                    activity=activity,
                    source_file=source_file,
                    action='APPROVED',
                    performed_by=None,  # System action
                    note='Auto-approved (no flags detected)'
                )

            # Audit log for ingestion
            AuditLog.objects.create(
                activity=activity,
                source_file=source_file,
                action='INGESTED',
                performed_by=self.user,
                note=f"Ingested from {source_file.original_filename} row {row_num}"
            )

        # Post-processing: Check if parser has finalization logic
        if hasattr(self.parser, 'finalize_parsing'):
            finalization_flags = self.parser.finalize_parsing()

            # Apply finalization flags
            for row_num, flag_names in finalization_flags.items():
                if row_num in activities_by_row:
                    activity = activities_by_row[row_num]
                    was_flagged = activity.is_suspicious
                    was_approved = activity.status == 'APPROVED'

                    # Apply all finalization flags at once (single save)
                    activity.flag(flag_names)

                    # Update flagged count if newly flagged
                    if not was_flagged and activity.is_suspicious:
                        stats['flagged'] += 1

                        # If was auto-approved, need to revert to PENDING and decrement approved count
                        if was_approved:
                            activity.status = 'PENDING'
                            activity.save()
                            stats['approved'] -= 1

                    # Log finalization flags
                    AuditLog.objects.create(
                        activity=activity,
                        source_file=source_file,
                        action='FLAGGED',
                        performed_by=None,
                        note=f"Post-processing flags: {', '.join(flag_names)}"
                    )

        return stats

    def _read_file_content(self) -> bytes:
        """
        Read file content as bytes.

        Handles both regular files and Django UploadedFile.

        Returns:
            File content as bytes
        """
        if hasattr(self.file_obj, 'read'):
            content = self.file_obj.read()
            self.file_obj.seek(0)  # Reset for potential re-reads

            # Convert to bytes if string
            if isinstance(content, str):
                content = content.encode('utf-8')

            return content
        else:
            # File path string
            with open(self.file_obj, 'rb') as f:
                return f.read()


# Import ParseResult for convenience
from apps.ingestion.parsers.base import ParseResult
