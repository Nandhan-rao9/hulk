"""
Core utility functions.
"""
from datetime import date
from django.db.models import Q


def is_period_locked(org, period_end_date):
    """
    Check if a reporting period is locked for the given organization.

    Args:
        org (Organization): Organization instance
        period_end_date (date): Activity period_end date

    Returns:
        bool: True if period is locked

    Example:
        if is_period_locked(activity.org, activity.period_end):
            raise PermissionError("Period is locked")
    """
    from apps.core.models import ReportingPeriodLock

    # Get first day of month for the activity
    period_month = period_end_date.replace(day=1)

    # Check if locked
    lock = ReportingPeriodLock.objects.filter(
        org=org,
        period_month=period_month,
        is_locked=True
    ).first()

    return lock is not None
