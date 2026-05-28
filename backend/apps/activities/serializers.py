"""
Activity serializers for REST API.

Provides nested serialization of Activity + Detail tables for review queue.
"""
from rest_framework import serializers
from apps.activities.models import Activity, SAPDetail, UtilityDetail, TravelDetail
from apps.ingestion.models import SourceFile


class SAPDetailSerializer(serializers.ModelSerializer):
    """Serializer for SAP material document details."""

    class Meta:
        model = SAPDetail
        fields = [
            'plant_code',
            'material_number',
            'material_desc',
            'material_group',
            'quantity_raw',
            'unit_raw',
            'quantity_normalized',
            'unit_normalized',
            'conversion_factor',
            'conversion_note',
            'movement_type',
            'vendor_number',
            'po_number',
            'classification_method',
        ]


class UtilityDetailSerializer(serializers.ModelSerializer):
    """Serializer for utility bill details."""

    class Meta:
        model = UtilityDetail
        fields = [
            'service_number',
            'tariff_category',
            'kwh_consumed',
            'unit_raw',
            'billing_amount_inr',
            'grid_emission_factor',
            'emission_factor_source',
        ]


class TravelDetailSerializer(serializers.ModelSerializer):
    """Serializer for travel expense details."""

    class Meta:
        model = TravelDetail
        fields = [
            'trip_id',
            'employee_id',
            'department',
            'cost_center',
            'mode',
            'origin',
            'destination',
            'distance_km',
            'cabin_class',
            'cabin_class_raw',
            'nights',
            'amount_raw',
            'currency',
            'amount_inr',
            'distance_method',
        ]


class ActivityListSerializer(serializers.ModelSerializer):
    """
    Serializer for activity list view (review queue).

    Includes nested detail data and source file info.
    """
    source_file_name = serializers.CharField(source='source_file.original_filename', read_only=True)
    source_type = serializers.CharField(source='source_file.source_type', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True, allow_null=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)

    # Conditional detail fields (only one will be populated based on source_type)
    sap_detail = SAPDetailSerializer(read_only=True)
    utility_detail = UtilityDetailSerializer(read_only=True)
    travel_detail = TravelDetailSerializer(read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id',
            'source_file_name',
            'source_type',
            'facility',
            'facility_name',
            'scope',
            'category',
            'period_start',
            'period_end',
            'emissions_kgco2e',
            'status',
            'is_suspicious',
            'flag_reason',
            'is_cross_month',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'created_at',
            # Detail data (conditional)
            'sap_detail',
            'utility_detail',
            'travel_detail',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'approved_at',
        ]


class ActivityApprovalSerializer(serializers.Serializer):
    """Serializer for activity approval action."""

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional note for approval audit log"
    )

    def update(self, instance, validated_data):
        """
        Approve the activity.

        Args:
            instance: Activity instance
            validated_data: Dict with optional 'note'

        Returns:
            Updated Activity instance
        """
        user = self.context['request'].user
        note = validated_data.get('note', '')

        # Use Activity.approve() helper method
        instance.approve(user, note)

        return instance
