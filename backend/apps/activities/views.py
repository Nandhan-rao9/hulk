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

        Behavior depends on user role:
        - Analyst: Moves activity to PENDING (waiting for admin)
        - Admin: Moves activity to APPROVED (final sign-off)

        Request body (optional):
        {
            "note": "Reviewed and approved"
        }

        Returns:
            200: Activity approved successfully
            400: Activity already approved/locked, or invalid state
            403: Permission denied
            404: Activity not found
        """
        activity = self.get_object()
        user = request.user

        # Check if already locked
        if activity.status == 'LOCKED':
            return Response(
                {'detail': 'Activity is locked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already approved
        if activity.status == 'APPROVED':
            return Response(
                {'detail': 'Activity already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = request.data.get('note', '')

        try:
            if user.is_admin():
                # Admin can directly approve
                activity.approve_by_admin(user, note)
                message = 'Activity approved by admin'
            elif user.is_analyst():
                # Analyst moves to pending
                activity.approve_by_analyst(user, note)
                message = 'Activity moved to pending (waiting for admin approval)'
            else:
                return Response(
                    {'detail': 'User does not have permission to approve activities'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Return updated activity
            activity.refresh_from_db()
            response_serializer = ActivityListSerializer(activity)
            return Response({
                'message': message,
                'activity': response_serializer.data
            })

        except PermissionError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """
        Manually flag an activity as suspicious. Only admins can flag.

        Can be used to:
        - Flag activities during review
        - Re-flag a PENDING or APPROVED activity if an error is discovered

        Request body:
        {
            "reason": "incorrect_plant_code",
            "note": "Plant code doesn't match facility records"
        }

        Returns:
            200: Activity flagged successfully
            400: Invalid request or activity cannot be flagged
            403: Permission denied (only admins can flag)
            404: Activity not found
        """
        activity = self.get_object()
        user = request.user

        # Only admins can flag
        if not user.is_admin():
            return Response(
                {'detail': 'Only admins can flag activities'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Don't allow flagging locked/invalidated
        if activity.status in ['LOCKED', 'INVALIDATED']:
            return Response(
                {'detail': f'Cannot flag {activity.status.lower()} activity'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Track if we're re-flagging an approved activity
        was_approved = activity.status == 'APPROVED'

        reason = request.data.get('reason')
        note = request.data.get('note', '')

        if not reason:
            return Response(
                {'detail': 'Flag reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use model method (includes audit log)
            activity.flag(reason, flagged_by=user)

            # If activity was approved, revoke approval
            if was_approved:
                activity.approved_by = None
                activity.approved_at = None
                activity.save()

            # Return updated activity
            activity.refresh_from_db()
            response_serializer = ActivityListSerializer(activity)
            return Response(response_serializer.data)

        except PermissionError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post'])
    def unflag(self, request, pk=None):
        """
        Remove suspicious flag from an activity. Only admins can unflag.

        Request body (optional):
        {
            "note": "Verified with vendor - amount is correct"
        }

        Returns:
            200: Activity unflagged successfully
            400: Activity is not flagged or cannot be unflagged
            403: Permission denied (only admins can unflag)
            404: Activity not found
        """
        activity = self.get_object()
        user = request.user

        # Only admins can unflag
        if not user.is_admin():
            return Response(
                {'detail': 'Only admins can unflag activities'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not activity.is_suspicious:
            return Response(
                {'detail': 'Activity is not flagged'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if activity.status in ['LOCKED', 'INVALIDATED']:
            return Response(
                {'detail': f'Cannot unflag {activity.status.lower()} activity'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = request.data.get('note', '')

        try:
            # Use model method (includes audit log and counter sync)
            activity.unflag(user, note)

            # Return updated activity
            activity.refresh_from_db()
            response_serializer = ActivityListSerializer(activity)
            return Response(response_serializer.data)

        except PermissionError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
