"""
Ingestion API views.

Handles file upload and SourceFile management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from apps.ingestion.models import SourceFile
from apps.ingestion.serializers import SourceFileSerializer, FileUploadSerializer


class SourceFileViewSet(viewsets.ModelViewSet):
    """
    SourceFile API viewset.

    List endpoint (/api/source-files/):
    - Returns paginated list of uploaded files
    - Supports ordering (?ordering=-uploaded_at)
    - Filtered by user's organization

    Retrieve endpoint (/api/source-files/{id}/):
    - Returns single source file with ingestion stats

    Delete endpoint (/api/source-files/{id}/):
    - DELETE source file and all related activities (admin only)

    Custom actions:
    - POST /api/source-files/upload/ - Upload and ingest CSV file
    """

    serializer_class = SourceFileSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['uploaded_at', 'status', 'source_type']
    ordering = ['-uploaded_at']  # Default ordering
    http_method_names = ['get', 'post', 'delete']  # Allow GET, POST, DELETE only

    def get_queryset(self):
        """
        Get queryset filtered by user's organization.

        Returns:
            QuerySet of SourceFile instances for user's org
        """
        user = self.request.user
        queryset = SourceFile.objects.filter(org=user.org)

        # Select related to avoid N+1 queries
        queryset = queryset.select_related('uploaded_by', 'org')

        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        Delete source file (admin only).

        Cascades to delete:
        - All activities from this file
        - All raw records
        - All audit logs

        Returns:
            204: File deleted successfully
            403: User is not admin
        """
        # Check admin permission
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Admin role required to delete files'},
                status=status.HTTP_403_FORBIDDEN
            )

        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        serializer_class=FileUploadSerializer,
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload(self, request):
        """
        Upload and ingest a CSV file.

        Request (multipart/form-data):
        - file: CSV file
        - source_type: SAP, UTILITY, TRAVEL_CONCUR, or TRAVEL_NAVAN

        Returns:
            201: File uploaded and ingested successfully
            400: Validation error or ingestion failure
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Trigger ingestion (handled in serializer.create())
        source_file = serializer.save()

        # Return created source file with stats
        response_serializer = SourceFileSerializer(source_file)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get summary statistics for this source file.

        Returns:
            200: Summary with status counts, emissions total, and source-specific metrics
        """
        from apps.activities.models import Activity, SAPDetail, UtilityDetail, TravelDetail
        from django.db.models import Count, Sum, Q
        from decimal import Decimal

        source_file = self.get_object()

        # Status counts
        status_counts = Activity.objects.filter(
            source_file=source_file
        ).values('status').annotate(count=Count('id'))

        status_dict = {item['status']: item['count'] for item in status_counts}

        # Emissions total (0 for now as not calculated)
        emissions_total = Decimal('0')

        # Source-specific metrics
        metrics = {}

        if source_file.source_type == 'SAP':
            # SAP: total quantity normalized + unit distribution
            sap_activities = Activity.objects.filter(
                source_file=source_file,
                status='APPROVED'
            ).select_related('sap_detail')

            total_quantity = Decimal('0')
            unit_distribution = {}
            material_breakdown = []

            for activity in sap_activities:
                if hasattr(activity, 'sap_detail'):
                    detail = activity.sap_detail
                    total_quantity += detail.quantity_normalized

                    # Unit distribution
                    unit = detail.unit_normalized
                    unit_distribution[unit] = unit_distribution.get(unit, Decimal('0')) + detail.quantity_normalized

                    # Material breakdown
                    material_breakdown.append({
                        'material': detail.material_desc,
                        'quantity': float(detail.quantity_normalized),
                        'unit': detail.unit_normalized
                    })

            metrics = {
                'total_quantity_normalized': float(total_quantity),
                'unit_distribution': {k: float(v) for k, v in unit_distribution.items()},
                'material_breakdown': material_breakdown
            }

        elif source_file.source_type == 'UTILITY':
            # Utility: total kWh
            total_kwh = Activity.objects.filter(
                source_file=source_file,
                status='APPROVED'
            ).aggregate(
                total=Sum('utility_detail__kwh_consumed')
            )['total'] or Decimal('0')

            metrics = {
                'total_kwh': float(total_kwh)
            }

        elif source_file.source_type in ['TRAVEL_CONCUR', 'TRAVEL_NAVAN']:
            # Travel: total distance km + breakdown by mode
            travel_activities = Activity.objects.filter(
                source_file=source_file,
                status='APPROVED'
            ).select_related('travel_detail')

            total_distance = Decimal('0')
            mode_breakdown = {}

            for activity in travel_activities:
                if hasattr(activity, 'travel_detail'):
                    detail = activity.travel_detail
                    if detail.distance_km:
                        total_distance += detail.distance_km
                        mode_breakdown[detail.mode] = mode_breakdown.get(detail.mode, Decimal('0')) + detail.distance_km

            metrics = {
                'total_distance_km': float(total_distance),
                'mode_breakdown': {k: float(v) for k, v in mode_breakdown.items()}
            }

        return Response({
            'source_file_id': source_file.id,
            'source_type': source_file.source_type,
            'status_counts': status_dict,
            'emissions_total_kgco2e': float(emissions_total),
            'metrics': metrics
        })

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """
        Get approved activities for this source file with key metrics.

        Returns summary showing:
        - For SAP: quantity consumed
        - For Utility: units (kWh) consumed
        - For Travel: kilometers traveled
        - Emissions (0 for now, calculation pending)

        Returns:
            200: List of approved activities with metrics
        """
        from apps.activities.models import Activity, SAPDetail, UtilityDetail, TravelDetail
        from decimal import Decimal

        source_file = self.get_object()

        # Get approved activities only
        activities = Activity.objects.filter(
            source_file=source_file,
            status='APPROVED'
        ).select_related('facility').prefetch_related(
            'sap_detail', 'utility_detail', 'travel_detail'
        )

        results = []
        for activity in activities:
            # Base data
            data = {
                'id': activity.id,
                'scope': activity.scope,
                'category': activity.category,
                'period_end': activity.period_end,
                'facility_name': activity.facility.name if activity.facility else None,
                'emissions_kgco2e': float(activity.emissions_kgco2e) if activity.emissions_kgco2e else 0,
            }

            # Add source-specific metrics
            if hasattr(activity, 'sap_detail'):
                detail = activity.sap_detail
                data['metric_label'] = 'Quantity'
                data['metric_value'] = float(detail.quantity_normalized)
                data['metric_unit'] = detail.unit_normalized
                data['material'] = detail.material_desc

            elif hasattr(activity, 'utility_detail'):
                detail = activity.utility_detail
                data['metric_label'] = 'Consumption'
                data['metric_value'] = float(detail.kwh_consumed)
                data['metric_unit'] = 'kWh'
                data['service_number'] = detail.service_number

            elif hasattr(activity, 'travel_detail'):
                detail = activity.travel_detail
                if detail.distance_km:
                    data['metric_label'] = 'Distance'
                    data['metric_value'] = float(detail.distance_km)
                    data['metric_unit'] = 'km'
                elif detail.nights:
                    data['metric_label'] = 'Nights'
                    data['metric_value'] = detail.nights
                    data['metric_unit'] = 'nights'
                else:
                    data['metric_label'] = 'Amount'
                    data['metric_value'] = float(detail.amount_inr) if detail.amount_inr else 0
                    data['metric_unit'] = 'INR'
                data['mode'] = detail.mode
                data['employee_id'] = detail.employee_id
                data['cabin_class'] = detail.cabin_class
                data['distance_km'] = float(detail.distance_km) if detail.distance_km else None
                data['nights'] = detail.nights

            results.append(data)

        return Response({
            'source_file_id': source_file.id,
            'filename': source_file.original_filename,
            'source_type': source_file.source_type,
            'total_approved': len(results),
            'activities': results
        })
