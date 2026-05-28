"""
Activity API views.

Provides REST endpoints for review queue and approval workflow.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from django.db.models import Q

from apps.activities.models import Activity
from apps.activities.serializers import ActivityListSerializer, ActivityApprovalSerializer


class ActivityFilter(filters.FilterSet):
    """
    Filter for Activity review queue.

    Supports filtering by:
    - status (exact match or multiple)
    - is_suspicious (boolean)
    - scope (exact match)
    - category (exact match)
    - facility (exact match by ID)
    - period_start (gte/lte range)
    - period_end (gte/lte range)
    - source_type (from related SourceFile)
    """

    status = filters.MultipleChoiceFilter(
        choices=Activity.STATUS_CHOICES,
        help_text="Filter by status (can pass multiple: ?status=PENDING&status=FLAGGED)"
    )
    is_suspicious = filters.BooleanFilter(
        help_text="Filter by suspicious flag (true/false)"
    )
    scope = filters.ChoiceFilter(
        choices=Activity.SCOPE_CHOICES,
        help_text="Filter by scope (1, 2, or 3)"
    )
    category = filters.ChoiceFilter(
        choices=Activity.CATEGORY_CHOICES,
        help_text="Filter by category (DIESEL, ELECTRICITY, FLIGHT, etc.)"
    )
    facility = filters.NumberFilter(
        field_name='facility__id',
        help_text="Filter by facility ID"
    )
    period_start_gte = filters.DateFilter(
        field_name='period_start',
        lookup_expr='gte',
        help_text="Filter by period start >= date (YYYY-MM-DD)"
    )
    period_start_lte = filters.DateFilter(
        field_name='period_start',
        lookup_expr='lte',
        help_text="Filter by period start <= date (YYYY-MM-DD)"
    )
    period_end_gte = filters.DateFilter(
        field_name='period_end',
        lookup_expr='gte',
        help_text="Filter by period end >= date (YYYY-MM-DD)"
    )
    period_end_lte = filters.DateFilter(
        field_name='period_end',
        lookup_expr='lte',
        help_text="Filter by period end <= date (YYYY-MM-DD)"
    )
    source_type = filters.ChoiceFilter(
        field_name='source_file__source_type',
        choices=[('SAP', 'SAP'), ('UTILITY', 'UTILITY'), ('TRAVEL_CONCUR', 'TRAVEL_CONCUR'), ('TRAVEL_NAVAN', 'TRAVEL_NAVAN')],
        help_text="Filter by source type"
    )
    search = filters.CharFilter(
        method='filter_search',
        help_text="Search across multiple fields (material desc, service number, employee ID, etc.)"
    )

    class Meta:
        model = Activity
        fields = [
            'status',
            'is_suspicious',
            'scope',
            'category',
            'facility',
            'period_start_gte',
            'period_start_lte',
            'period_end_gte',
            'period_end_lte',
            'source_type',
            'search',
        ]

    def filter_search(self, queryset, name, value):
        """
        Search filter across multiple detail fields.

        Searches in:
        - SAP: material_desc, material_number, plant_code
        - Utility: service_number
        - Travel: employee_id, trip_id
        """
        return queryset.filter(
            Q(sap_detail__material_desc__icontains=value) |
            Q(sap_detail__material_number__icontains=value) |
            Q(sap_detail__plant_code__icontains=value) |
            Q(utility_detail__service_number__icontains=value) |
            Q(travel_detail__employee_id__icontains=value) |
            Q(travel_detail__trip_id__icontains=value)
        ).distinct()


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Activity API viewset (read-only list/retrieve + custom actions).

    List endpoint (/api/activities/):
    - Returns paginated list of activities
    - Supports filtering (status, suspicious, scope, category, dates, source_type)
    - Supports ordering (?ordering=-period_end)
    - Includes nested detail data (SAP/Utility/Travel)

    Retrieve endpoint (/api/activities/{id}/):
    - Returns single activity with full detail

    Custom actions:
    - POST /api/activities/{id}/approve/ - Approve activity
    """

    serializer_class = ActivityListSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ActivityFilter
    ordering_fields = ['period_end', 'created_at', 'status', 'scope']
    ordering = ['-period_end', '-created_at']  # Default ordering

    def get_queryset(self):
        """
        Get queryset filtered by user's organization.

        Returns:
            QuerySet of Activity instances for user's org
        """
        user = self.request.user
        queryset = Activity.objects.filter(org=user.org)

        # Select related to avoid N+1 queries
        queryset = queryset.select_related(
            'source_file',
            'facility',
            'approved_by',
            'sap_detail',
            'utility_detail',
            'travel_detail',
        )

        return queryset

    @action(detail=True, methods=['post'], serializer_class=ActivityApprovalSerializer)
    def approve(self, request, pk=None):
        """
        Approve an activity.

        Request body (optional):
        {
            "note": "Reviewed and approved"
        }

        Returns:
            200: Activity approved successfully
            400: Activity already approved/locked
            404: Activity not found
        """
        activity = self.get_object()

        # Check if already approved or locked
        if activity.status in ['APPROVED', 'LOCKED']:
            return Response(
                {'detail': f'Activity already {activity.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and approve
        serializer = self.get_serializer(activity, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return updated activity
        activity.refresh_from_db()
        response_serializer = ActivityListSerializer(activity)
        return Response(response_serializer.data)
