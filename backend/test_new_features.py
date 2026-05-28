"""
Test script for new features: FX traceability, lookup uploads, file summary.

Run with: python manage.py shell < test_new_features.py
"""
from decimal import Decimal
from apps.activities.models import Activity, TravelDetail
from apps.core.models import CurrencyConversionRate
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*60)
print("TESTING NEW FEATURES")
print("="*60)

# Test 1: Check FX traceability fields exist
print("\n[TEST 1] TravelDetail FX fields exist:")
travel_fields = [f.name for f in TravelDetail._meta.get_fields()]
fx_fields = ['fx_rate_used', 'fx_rate_date', 'fx_source', 'fx_note']
for field in fx_fields:
    exists = field in travel_fields
    status = "✅" if exists else "❌"
    print(f"  {status} {field}: {'EXISTS' if exists else 'MISSING'}")

# Test 2: Check currency rates are seeded
print("\n[TEST 2] Currency conversion rates:")
rates = CurrencyConversionRate.objects.all()
print(f"  Total rates: {rates.count()}")
for rate in rates[:5]:
    print(f"  - {rate.currency_code}: {rate.rate_to_inr} INR (effective {rate.effective_date})")

# Test 3: Check if any travel activities have FX data
print("\n[TEST 3] Travel activities with FX data:")
travel_activities = Activity.objects.filter(
    traveldetail__isnull=False
).select_related('traveldetail')[:3]

if travel_activities.exists():
    for activity in travel_activities:
        detail = activity.traveldetail
        print(f"  Activity {activity.id}:")
        print(f"    Amount: {detail.amount_raw} {detail.currency}")
        if detail.amount_inr:
            print(f"    INR: {detail.amount_inr}")
        if detail.fx_rate_used:
            print(f"    FX Rate: {detail.fx_rate_used} ({detail.fx_source})")
        print(f"    Note: {detail.fx_note or 'None'}")
else:
    print("  No travel activities found yet. Upload travel CSV to test.")

# Test 4: Check admin user exists
print("\n[TEST 4] Admin user check:")
try:
    admin = User.objects.get(username='admin')
    print(f"  ✅ Admin user: {admin.username} (role: {admin.role})")
    print(f"  Organization: {admin.org.name if admin.org else 'None'}")
except User.DoesNotExist:
    print("  ❌ Admin user not found")

# Test 5: File summary endpoint readiness
print("\n[TEST 5] File summary endpoint components:")
from apps.ingestion.models import SourceFile
files = SourceFile.objects.all()
print(f"  Total source files: {files.count()}")
if files.exists():
    file = files.first()
    print(f"  Sample file: {file.original_filename} ({file.source_type})")
    approved = Activity.objects.filter(source_file=file, status='APPROVED').count()
    print(f"  Approved activities: {approved}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60 + "\n")
