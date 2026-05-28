"""
Generate sample CSV files for both organizations.
Run: python generate_sample_excels.py
"""

import pandas as pd
from datetime import datetime, timedelta
import random
import os

# Create sample_uploads directory
os.makedirs('sample_uploads', exist_ok=True)

print("[CSV] Generating sample CSV files for both organizations...")
print()

# ============================================================================
# ACME MANUFACTURING - SAP MB51 File
# ============================================================================

acme_sap_data = []
base_date = datetime(2024, 1, 1)

materials = [
    ('100001', 'Diesel Fuel - High Speed', 'FUEL-01', '1000'),  # Mumbai
    ('100002', 'Petrol - Regular', 'FUEL-02', '1000'),
    ('100003', 'LPG Gas Cylinder', 'FUEL-03', '2000'),  # Pune
    ('100004', 'Natural Gas', 'GAS-01', '2000'),
    ('100005', 'Diesel Fuel - High Speed', 'FUEL-01', '3000'),  # Delhi
]

for i in range(30):
    material = random.choice(materials)
    qty = round(random.uniform(50, 500), 2)

    acme_sap_data.append({
        'MATNR': material[0],  # Material number
        'MAKTX': material[1],  # Material Description
        'MATKL': material[2],  # Material Group
        'WERKS': material[3],  # Plant
        'BUDAT': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),  # Posting Date
        'MENGE': qty,  # Quantity
        'MEINS': 'L' if 'Diesel' in material[1] or 'Petrol' in material[1] else 'KG',  # Base Unit
        'BWART': '101',  # Movement Type
        'LIFNR': f'V{random.randint(1000, 9999)}',  # Vendor
        'EBELN': f'PO{random.randint(100000, 999999)}'  # Purchase Order
    })

df_acme_sap = pd.DataFrame(acme_sap_data)
df_acme_sap.to_csv('sample_uploads/ACME_SAP_MB51_JAN2024.csv', index=False)
print("[OK] Created: ACME_SAP_MB51_JAN2024.csv (30 rows)")

# ============================================================================
# ACME MANUFACTURING - Utility Bill
# ============================================================================

acme_utility_data = []

for i in range(10):
    acme_utility_data.append({
        'service_number': 'MH-METER-001' if i < 5 else 'MH-METER-002',
        'tariff_category': 'HT-1',
        'from_date': (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=i*3 + 30)).strftime('%Y-%m-%d'),
        'units': random.randint(5000, 15000),
        'unit': 'kWh',
        'amount': round(random.uniform(50000, 150000), 2)
    })

df_acme_utility = pd.DataFrame(acme_utility_data)
df_acme_utility.to_csv('sample_uploads/ACME_ELECTRICITY_JAN2024.csv', index=False)
print("[OK] Created: ACME_ELECTRICITY_JAN2024.csv (10 rows)")

# ============================================================================
# ACME MANUFACTURING - Travel (Concur)
# ============================================================================

acme_travel_data = []

flights = [
    ('BOM', 'DEL', 1400),
    ('DEL', 'BLR', 1740),
    ('BLR', 'BOM', 840),
    ('BOM', 'SIN', 3920),
    ('DEL', 'DXB', 2200),
]

for i in range(15):
    route = random.choice(flights)

    acme_travel_data.append({
        'trip_id': f'TRIP{random.randint(10000, 99999)}',
        'employee_id': f'EMP{random.randint(1000, 9999)}',
        'department': random.choice(['Operations', 'Sales', 'Management']),
        'cost_center': random.choice(['CC-100', 'CC-200', 'CC-300']),
        'expense_date': (base_date + timedelta(days=i*2)).strftime('%Y-%m-%d'),
        'mode': 'AIR',
        'origin': route[0],
        'destination': route[1],
        'cabin_class': random.choice(['Y', 'W', 'J']),
        'amount_raw': round(random.uniform(5000, 25000), 2),
        'currency': 'INR'
    })

df_acme_travel = pd.DataFrame(acme_travel_data)
df_acme_travel.to_csv('sample_uploads/ACME_TRAVEL_JAN2024.csv', index=False)
print("[OK] Created: ACME_TRAVEL_JAN2024.csv (15 rows)")

print()

# ============================================================================
# TECHCORP INDUSTRIES - SAP MB51 File
# ============================================================================

tech_sap_data = []

materials = [
    ('200001', 'Diesel - Industrial Grade', 'DIESEL', 'BLR-001'),
    ('200002', 'Petrol - Premium', 'PETROL', 'BLR-001'),
    ('200003', 'Electricity', 'ELEC', 'CHN-001'),
    ('200004', 'Natural Gas Pipeline', 'GAS', 'CHN-001'),
]

for i in range(25):
    material = random.choice(materials)
    qty = round(random.uniform(100, 800), 2)

    tech_sap_data.append({
        'MATNR': material[0],
        'MAKTX': material[1],
        'MATKL': material[2],
        'WERKS': material[3],
        'BUDAT': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
        'MENGE': qty,
        'MEINS': 'L' if 'Diesel' in material[1] or 'Petrol' in material[1] else 'M3',
        'BWART': '101',
        'LIFNR': f'VEN{random.randint(1000, 9999)}',
        'EBELN': f'PO-TECH-{random.randint(10000, 99999)}'
    })

df_tech_sap = pd.DataFrame(tech_sap_data)
df_tech_sap.to_csv('sample_uploads/TECHCORP_SAP_MB51_JAN2024.csv', index=False)
print("[OK] Created: TECHCORP_SAP_MB51_JAN2024.csv (25 rows)")

# ============================================================================
# TECHCORP INDUSTRIES - Utility Bill
# ============================================================================

tech_utility_data = []

for i in range(8):
    tech_utility_data.append({
        'service_number': 'KA-METER-100' if i < 4 else 'TN-METER-200',
        'tariff_category': 'HT-2',
        'from_date': (base_date + timedelta(days=i*4)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=i*4 + 30)).strftime('%Y-%m-%d'),
        'units': random.randint(8000, 20000),
        'unit': 'kWh',
        'amount': round(random.uniform(80000, 200000), 2)
    })

df_tech_utility = pd.DataFrame(tech_utility_data)
df_tech_utility.to_csv('sample_uploads/TECHCORP_ELECTRICITY_JAN2024.csv', index=False)
print("[OK] Created: TECHCORP_ELECTRICITY_JAN2024.csv (8 rows)")

# ============================================================================
# TECHCORP INDUSTRIES - Travel (Navan)
# ============================================================================

tech_travel_data = []

flights = [
    ('BLR', 'DEL', 1740),
    ('BLR', 'BOM', 840),
    ('CHN', 'HYD', 530),
    ('BLR', 'SFO', 13900),
    ('BLR', 'LHR', 8300),
]

for i in range(20):
    route = random.choice(flights)

    tech_travel_data.append({
        'trip_id': f'TECH-{random.randint(1000, 9999)}',
        'employee_id': f'TECH-EMP{random.randint(100, 999)}',
        'department': random.choice(['Engineering', 'Product', 'Sales', 'HR']),
        'cost_center': random.choice(['TECH-100', 'TECH-200', 'TECH-300']),
        'expense_date': (base_date + timedelta(days=i*2)).strftime('%Y-%m-%d'),
        'mode': 'AIR',
        'origin': route[0],
        'destination': route[1],
        'cabin_class': random.choice(['Y', 'Y', 'W', 'J']),
        'amount_raw': round(random.uniform(4000, 35000), 2),
        'currency': 'INR' if route[2] < 5000 else random.choice(['INR', 'USD'])
    })

df_tech_travel = pd.DataFrame(tech_travel_data)
df_tech_travel.to_csv('sample_uploads/TECHCORP_TRAVEL_JAN2024.csv', index=False)
print("[OK] Created: TECHCORP_TRAVEL_JAN2024.csv (20 rows)")

print()
print("=" * 60)
print("[OK] All sample CSV files created in sample_uploads/")
print("=" * 60)
print()
print("[FILES] Files created:")
print("   ACME MANUFACTURING:")
print("   - ACME_SAP_MB51_JAN2024.csv (30 rows)")
print("   - ACME_ELECTRICITY_JAN2024.csv (10 rows)")
print("   - ACME_TRAVEL_JAN2024.csv (15 rows)")
print()
print("   TECHCORP INDUSTRIES:")
print("   - TECHCORP_SAP_MB51_JAN2024.csv (25 rows)")
print("   - TECHCORP_ELECTRICITY_JAN2024.csv (8 rows)")
print("   - TECHCORP_TRAVEL_JAN2024.csv (20 rows)")
print()
print("[NOTE] Upload instructions:")
print("   1. Log in as acme_admin or acme_analyst")
print("   2. Upload ACME_* files")
print("   3. Log out and log in as tech_admin or tech_analyst")
print("   4. Upload TECHCORP_* files")
print()
