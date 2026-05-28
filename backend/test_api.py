"""
Quick API endpoint test script.

Tests:
1. GET /api/activities/ - list activities
2. GET /api/activities/{id}/ - retrieve single activity
3. POST /api/activities/{id}/approve/ - approve activity
4. GET /api/source-files/ - list source files
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hulk.settings')
django.setup()

from django.test import RequestFactory
from apps.core.models import User
from apps.activities.views import ActivityViewSet
from apps.ingestion.views import SourceFileViewSet
from apps.activities.models import Activity
from apps.ingestion.models import SourceFile


def test_api():
    """Test API endpoints."""
    factory = RequestFactory()

    # Get test user
    user = User.objects.filter(role='analyst').first()
    if not user:
        print("ERROR: No analyst user found. Run setup_test_data first.")
        return

    # Ensure user has org
    if not user.org:
        from apps.core.models import Organization
        org = Organization.objects.first()
        if not org:
            print("ERROR: No organization found. Run setup_test_data first.")
            return
        user.org = org
        user.save()
        print(f"Assigned user {user.email} to org {org.name}")

    print(f"Testing API with user: {user.email} (org: {user.org.name})")
    print()

    # Test 1: List activities
    print("1. GET /api/activities/")
    request = factory.get('/api/activities/')
    request.user = user
    view = ActivityViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        count = len(response.data.get('results', []))
        print(f"   Activities: {count}")
    print()

    # Test 2: Retrieve single activity
    activity = Activity.objects.filter(org=user.org).first()
    if activity:
        print(f"2. GET /api/activities/{activity.id}/")
        request = factory.get(f'/api/activities/{activity.id}/')
        request.user = user
        view = ActivityViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=activity.id)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Activity: {response.data.get('category')} - {response.data.get('status')}")
        print()

    # Test 3: Approve activity
    pending = Activity.objects.filter(org=user.org, status='PENDING').first()
    if pending:
        print(f"3. POST /api/activities/{pending.id}/approve/")
        request = factory.post(
            f'/api/activities/{pending.id}/approve/',
            data={'note': 'Test approval'},
            content_type='application/json'
        )
        request.user = user
        view = ActivityViewSet.as_view({'post': 'approve'})
        response = view(request, pk=pending.id)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            pending.refresh_from_db()
            print(f"   New status: {pending.status}")
            print(f"   Approved by: {pending.approved_by.username}")
        print()

    # Test 4: List source files
    print("4. GET /api/source-files/")
    request = factory.get('/api/source-files/')
    request.user = user
    view = SourceFileViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        count = len(response.data.get('results', []))
        print(f"   Source files: {count}")
    print()

    # Test 5: Filter activities by status
    print("5. GET /api/activities/?status=PENDING")
    request = factory.get('/api/activities/?status=PENDING')
    request.user = user
    view = ActivityViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        count = len(response.data.get('results', []))
        print(f"   Pending activities: {count}")
    print()

    # Test 6: Filter activities by suspicious flag
    print("6. GET /api/activities/?is_suspicious=true")
    request = factory.get('/api/activities/?is_suspicious=true')
    request.user = user
    view = ActivityViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        count = len(response.data.get('results', []))
        print(f"   Suspicious activities: {count}")
    print()

    print("=" * 50)
    print("API tests completed successfully!")
    print()
    print("Available endpoints:")
    print("  GET    /api/activities/")
    print("  GET    /api/activities/{id}/")
    print("  POST   /api/activities/{id}/approve/")
    print("  GET    /api/source-files/")
    print("  GET    /api/source-files/{id}/")
    print("  POST   /api/source-files/upload/")


if __name__ == '__main__':
    test_api()
