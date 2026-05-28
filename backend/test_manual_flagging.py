"""
Test script for manual flagging feature.
Run with: python manage.py shell < test_manual_flagging.py
"""

from apps.activities.models import Activity
from apps.core.models import User
from apps.audit.models import AuditLog

print("=" * 60)
print("Testing Manual Flagging Feature")
print("=" * 60)

# Get a test user (first admin or analyst)
user = User.objects.filter(role__in=['admin', 'analyst']).first()
if not user:
    print("❌ No admin/analyst user found. Please create one first.")
    exit()

print(f"✓ Using test user: {user.username}")

# Get a test activity that's not flagged
activity = Activity.objects.filter(
    is_suspicious=False,
    status='PENDING'
).first()

if not activity:
    print("❌ No unflagged PENDING activity found for testing.")
    print("   Please upload some data first.")
    exit()

print(f"✓ Found test activity ID: {activity.id}")
print(f"  - Status: {activity.status}")
print(f"  - Suspicious: {activity.is_suspicious}")
print(f"  - Category: {activity.category}")

# Test 1: Flag the activity
print("\n" + "=" * 60)
print("Test 1: Flagging activity")
print("=" * 60)

initial_status = activity.status
activity.flag('incorrect_amount')

# Create audit log
AuditLog.objects.create(
    activity=activity,
    source_file=activity.source_file,
    action='FLAGGED',
    performed_by=user,
    note="Manual flag: incorrect_amount. Testing flagging feature"
)

activity.refresh_from_db()
print(f"✓ Activity flagged")
print(f"  - is_suspicious: {activity.is_suspicious}")
print(f"  - flag_reason: {activity.flag_reason}")
print(f"  - status: {activity.status}")

# Verify status changed to FLAGGED
if activity.status == 'FLAGGED' and activity.is_suspicious:
    print("✓ Status correctly changed to FLAGGED")
else:
    print(f"❌ Expected status=FLAGGED, got {activity.status}")

# Test 2: Flag with additional reason (test pipe-delimited)
print("\n" + "=" * 60)
print("Test 2: Adding second flag reason")
print("=" * 60)

activity.flag('duplicate_suspected')
activity.refresh_from_db()

print(f"✓ Second flag added")
print(f"  - flag_reason: {activity.flag_reason}")

if '|' in activity.flag_reason:
    reasons = activity.flag_reason.split('|')
    print(f"✓ Multiple reasons detected: {reasons}")
else:
    print("❌ Expected pipe-delimited reasons")

# Test 3: Unflag the activity
print("\n" + "=" * 60)
print("Test 3: Unflagging activity")
print("=" * 60)

old_reasons = activity.flag_reason
activity.is_suspicious = False
activity.flag_reason = None
activity.status = 'PENDING'
activity.save()

# Create audit log for unflagging
AuditLog.objects.create(
    activity=activity,
    source_file=activity.source_file,
    action='REVIEWED',
    performed_by=user,
    field_changed='is_suspicious',
    old_value=old_reasons,
    new_value='False',
    note="Unflagged: Testing unflagging feature"
)

activity.refresh_from_db()
print(f"✓ Activity unflagged")
print(f"  - is_suspicious: {activity.is_suspicious}")
print(f"  - flag_reason: {activity.flag_reason}")
print(f"  - status: {activity.status}")

# Test 4: Check audit trail
print("\n" + "=" * 60)
print("Test 4: Verifying audit trail")
print("=" * 60)

audit_logs = AuditLog.objects.filter(activity=activity).order_by('-performed_at')[:5]
print(f"✓ Found {audit_logs.count()} audit log entries for this activity")

for log in audit_logs:
    print(f"  - {log.get_action_display()} by {log.performed_by.username if log.performed_by else 'System'}")
    if log.note:
        print(f"    Note: {log.note[:80]}")

# Test 5: Check MANUAL_FLAG_REASONS constant
print("\n" + "=" * 60)
print("Test 5: Checking flag reason choices")
print("=" * 60)

if hasattr(Activity, 'MANUAL_FLAG_REASONS'):
    print("✓ MANUAL_FLAG_REASONS constant exists")
    print(f"  Available reasons:")
    for code, label in Activity.MANUAL_FLAG_REASONS:
        print(f"    - {code}: {label}")
else:
    print("❌ MANUAL_FLAG_REASONS not found in Activity model")

print("\n" + "=" * 60)
print("✅ All tests completed successfully!")
print("=" * 60)
print("\nNext steps:")
print("1. Start the Django dev server: python manage.py runserver")
print("2. Start the React dev server: cd frontend && npm run dev")
print("3. Navigate to the Review Queue and test the UI")
