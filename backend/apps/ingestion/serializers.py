"""
Ingestion serializers for REST API.

Handles file upload and SourceFile listing.
"""
from rest_framework import serializers
from apps.ingestion.models import SourceFile


class SourceFileSerializer(serializers.ModelSerializer):
    """Serializer for SourceFile model (uploaded files list)."""

    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    org_name = serializers.CharField(source='org.name', read_only=True)

    class Meta:
        model = SourceFile
        fields = [
            'id',
            'org',
            'org_name',
            'source_type',
            'original_filename',
            'file_hash',
            'uploaded_by',
            'uploaded_by_name',
            'uploaded_at',
            'status',
            'total_rows',
            'failed_rows',
            'flagged_rows',
            'pending_rows',
            'approved_rows',
        ]
        read_only_fields = [
            'id',
            'file_hash',
            'uploaded_at',
            'status',
            'total_rows',
            'failed_rows',
            'flagged_rows',
            'pending_rows',
            'approved_rows',
        ]


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload endpoint.

    Handles CSV file upload with source type selection.
    """
    file = serializers.FileField(
        help_text="CSV file to upload"
    )
    source_type = serializers.ChoiceField(
        choices=['SAP', 'UTILITY', 'TRAVEL_CONCUR', 'TRAVEL_NAVAN'],
        help_text="Source type: SAP, UTILITY, TRAVEL_CONCUR, or TRAVEL_NAVAN"
    )

    def validate_file(self, value):
        """
        Validate uploaded file.

        Checks:
        - File extension is .csv
        - File size < 50MB

        Args:
            value: UploadedFile instance

        Returns:
            Validated file

        Raises:
            ValidationError: If validation fails
        """
        # Check extension
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError(
                "File must be a CSV file (.csv extension)"
            )

        # Check size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds 50MB limit (got {value.size / (1024 * 1024):.1f}MB)"
            )

        return value

    def create(self, validated_data):
        """
        Process file upload and trigger ingestion.

        Args:
            validated_data: Dict with 'file' and 'source_type'

        Returns:
            SourceFile instance

        Raises:
            ValidationError: If ingestion fails
        """
        from apps.ingestion.services.ingestion_service import IngestionService

        file_obj = validated_data['file']
        source_type = validated_data['source_type']
        user = self.context['request'].user
        org = user.org

        if not org:
            raise serializers.ValidationError("User must be assigned to an organization")

        # Trigger ingestion
        try:
            service = IngestionService(file_obj, source_type, org, user)
            source_file = service.ingest()
            return source_file
        except ValueError as e:
            # Handle duplicate file or validation errors
            raise serializers.ValidationError(str(e))
        except Exception as e:
            # Handle unexpected errors
            import traceback
            error_detail = f"Ingestion failed: {str(e)}\n{traceback.format_exc()}"
            print(error_detail)  # Log to console for debugging
            raise serializers.ValidationError(f"Ingestion failed: {str(e)}")
