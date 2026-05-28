"""
Generate sample CSV files with intentional flags for demonstration.
Run: python generate_flagged_samples.py
"""

import pandas as pd
from datetime import datetime, timedelta
import random
import os

# Create sample_uploads directory
os.makedirs('sample_uploads', exist_ok=True)

print("[DEMO] Generating CSV files with flagged rows for demonstration...")
print()

base_date = datetime(2024, 1, 1)

# ============================================================================
# ACME MANUFACTURING - SAP MB51 File (with flags)
# ============================================================================

acme_sap_data = []

# CLEAN ROWS (15 rows)
materials = [
    ('100001', 'Diesel Fuel - High Speed', 'FUEL-01', '1000'),
    ('100002', 'Petrol - Regular', 'FUEL-02', '1000'),
    ('100003', 'LPG Gas Cylinder', 'FUEL-03', '2000'),
    ('100004', 'Natural Gas', 'GAS-01', '2000'),
]

for i in range(15):
    material = random.choice(materials)
    qty = round(random.uniform(50, 500), 2)
    acme_sap_data.append({
        'MATNR': material[0],
        'MAKTX': material[1],
        'MATKL': material[2],
        'WERKS': material[3],
        'BUDAT': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
        'MENGE': qty,
        'MEINS': 'L' if 'Diesel' in material[1] or 'Petrol' in material[1] else 'KG',
        'BWART': '101',
        'LIFNR': f'V{random.randint(1000, 9999)}',
        'EBELN': f'PO{random.randint(100000, 999999)}'
    })

# FLAG 1: Unknown Plant (3 rows) - Plant code not in lookup table
for i in range(3):
    material = random.choice(materials)
    acme_sap_data.append({
        'MATNR': material[0],
        'MAKTX': material[1],
        'MATKL': material[2],
        'WERKS': '9999',  # Unknown plant code
        'BUDAT': (base_date + timedelta(days=15+i)).strftime('%Y-%m-%d'),
        'MENGE': round(random.uniform(50, 200), 2),
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'V{random.randint(1000, 9999)}',
        'EBELN': f'PO{random.randint(100000, 999999)}'
    })

# FLAG 2: Unknown Material (3 rows) - Material group not in mapping
for i in range(3):
    acme_sap_data.append({
        'MATNR': '100099',
        'MAKTX': 'Unknown Material Type',
        'MATKL': 'UNKNOWN-MAT',  # Not in material mapping
        'WERKS': '1000',
        'BUDAT': (base_date + timedelta(days=18+i)).strftime('%Y-%m-%d'),
        'MENGE': round(random.uniform(50, 200), 2),
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'V{random.randint(1000, 9999)}',
        'EBELN': f'PO{random.randint(100000, 999999)}'
    })

# FLAG 3: Negative Quantity (2 rows) - Should be returns but flagged
for i in range(2):
    material = random.choice(materials)
    acme_sap_data.append({
        'MATNR': material[0],
        'MAKTX': material[1],
        'MATKL': material[2],
        'WERKS': material[3],
        'BUDAT': (base_date + timedelta(days=21+i)).strftime('%Y-%m-%d'),
        'MENGE': -round(random.uniform(10, 50), 2),  # Negative!
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'V{random.randint(1000, 9999)}',
        'EBELN': f'PO{random.randint(100000, 999999)}'
    })

# FLAG 4: Duplicate Rows (2 identical rows)
dup_row = {
    'MATNR': '100001',
    'MAKTX': 'Diesel Fuel - High Speed',
    'MATKL': 'FUEL-01',
    'WERKS': '1000',
    'BUDAT': '2024-01-25',
    'MENGE': 123.45,
    'MEINS': 'L',
    'BWART': '101',
    'LIFNR': 'V1234',
    'EBELN': 'PO123456'
}
acme_sap_data.append(dup_row)
acme_sap_data.append(dup_row.copy())  # Duplicate!

# FLAG 5: Unit Inconsistency (2 rows) - Diesel in KG instead of L
for i in range(2):
    acme_sap_data.append({
        'MATNR': '100001',
        'MAKTX': 'Diesel Fuel - High Speed',
        'MATKL': 'FUEL-01',
        'WERKS': '1000',
        'BUDAT': (base_date + timedelta(days=26+i)).strftime('%Y-%m-%d'),
        'MENGE': round(random.uniform(100, 300), 2),
        'MEINS': 'KG',  # Should be L for diesel!
        'BWART': '101',
        'LIFNR': f'V{random.randint(1000, 9999)}',
        'EBELN': f'PO{random.randint(100000, 999999)}'
    })

df_acme_sap = pd.DataFrame(acme_sap_data)
df_acme_sap.to_csv('sample_uploads/ACME_SAP_MB51_JAN2024.csv', index=False)
print(f"[OK] ACME_SAP_MB51_JAN2024.csv ({len(acme_sap_data)} rows)")
print("     - 15 clean rows")
print("     - 3 unknown_plant")
print("     - 3 unknown_material")
print("     - 2 negative_quantity")
print("     - 2 duplicate_row")
print("     - 2 unit_inconsistency")
print()

# ============================================================================
# ACME MANUFACTURING - Utility Bill (with flags)
# ============================================================================

acme_utility_data = []

# CLEAN ROWS (6 rows)
for i in range(6):
    acme_utility_data.append({
        'service_number': 'MH-METER-001' if i < 3 else 'MH-METER-002',
        'tariff_category': 'HT-1',
        'from_date': (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=i*30 + 28)).strftime('%Y-%m-%d'),
        'units': random.randint(5000, 15000),
        'unit': 'kWh',
        'amount': round(random.uniform(50000, 150000), 2)
    })

# FLAG 1: Unknown Meter (2 rows)
for i in range(2):
    acme_utility_data.append({
        'service_number': 'UNKNOWN-METER-999',  # Not in lookup
        'tariff_category': 'HT-1',
        'from_date': (base_date + timedelta(days=180+i*30)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=180+i*30 + 28)).strftime('%Y-%m-%d'),
        'units': random.randint(5000, 15000),
        'unit': 'kWh',
        'amount': round(random.uniform(50000, 150000), 2)
    })

# FLAG 2: Negative Consumption (1 row)
acme_utility_data.append({
    'service_number': 'MH-METER-001',
    'tariff_category': 'HT-1',
    'from_date': '2024-01-20',
    'to_date': '2024-02-18',
    'units': -5000,  # Negative!
    'unit': 'kWh',
    'amount': round(random.uniform(50000, 150000), 2)
})

# FLAG 3: Unit Ambiguous (kVAh instead of kWh) (2 rows)
for i in range(2):
    acme_utility_data.append({
        'service_number': 'MH-METER-001',
        'tariff_category': 'HT-1',
        'from_date': (base_date + timedelta(days=240+i*30)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=240+i*30 + 28)).strftime('%Y-%m-%d'),
        'units': random.randint(8000, 18000),
        'unit': 'kVAh',  # Apparent power, not active!
        'amount': round(random.uniform(60000, 160000), 2)
    })

# FLAG 4: Negative Amount (1 row)
acme_utility_data.append({
    'service_number': 'MH-METER-002',
    'tariff_category': 'HT-1',
    'from_date': '2024-01-25',
    'to_date': '2024-02-23',
    'units': random.randint(5000, 15000),
    'unit': 'kWh',
    'amount': -50000.00  # Negative bill amount!
})

df_acme_utility = pd.DataFrame(acme_utility_data)
df_acme_utility.to_csv('sample_uploads/ACME_ELECTRICITY_JAN2024.csv', index=False)
print(f"[OK] ACME_ELECTRICITY_JAN2024.csv ({len(acme_utility_data)} rows)")
print("     - 6 clean rows")
print("     - 2 unknown_meter")
print("     - 1 negative_consumption")
print("     - 2 unit_ambiguous")
print("     - 1 negative_amount")
print()

# ============================================================================
# ACME MANUFACTURING - Travel (with flags)
# ============================================================================

acme_travel_data = []

# CLEAN ROWS (10 rows)
clean_flights = [
    ('BOM', 'DEL'),
    ('DEL', 'BLR'),
    ('BLR', 'BOM'),
]

for i in range(10):
    route = random.choice(clean_flights)
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

# FLAG 1: Unknown Airport (2 rows) - Airport code not in IATA database
for i in range(2):
    acme_travel_data.append({
        'trip_id': f'TRIP{random.randint(10000, 99999)}',
        'employee_id': f'EMP{random.randint(1000, 9999)}',
        'department': 'Sales',
        'cost_center': 'CC-100',
        'expense_date': (base_date + timedelta(days=20+i)).strftime('%Y-%m-%d'),
        'mode': 'AIR',
        'origin': 'BOM',
        'destination': 'XYZ',  # Unknown airport code
        'cabin_class': 'Y',
        'amount_raw': round(random.uniform(5000, 15000), 2),
        'currency': 'INR'
    })

# FLAG 2: Missing Airport (1 row) - No origin/destination
acme_travel_data.append({
    'trip_id': f'TRIP{random.randint(10000, 99999)}',
    'employee_id': f'EMP{random.randint(1000, 9999)}',
    'department': 'Operations',
    'cost_center': 'CC-200',
    'expense_date': '2024-01-22',
    'mode': 'AIR',
    'origin': '',  # Missing!
    'destination': '',  # Missing!
    'cabin_class': 'Y',
    'amount_raw': round(random.uniform(8000, 12000), 2),
    'currency': 'INR'
})

# FLAG 3: Unknown Cabin Class (1 row)
acme_travel_data.append({
    'trip_id': f'TRIP{random.randint(10000, 99999)}',
    'employee_id': f'EMP{random.randint(1000, 9999)}',
    'department': 'Management',
    'cost_center': 'CC-300',
    'expense_date': '2024-01-23',
    'mode': 'AIR',
    'origin': 'BOM',
    'destination': 'DEL',
    'cabin_class': 'X',  # Unknown class code
    'amount_raw': round(random.uniform(10000, 20000), 2),
    'currency': 'INR'
})

# FLAG 4: Negative Amount (1 row)
acme_travel_data.append({
    'trip_id': f'TRIP{random.randint(10000, 99999)}',
    'employee_id': f'EMP{random.randint(1000, 9999)}',
    'department': 'Sales',
    'cost_center': 'CC-100',
    'expense_date': '2024-01-24',
    'mode': 'AIR',
    'origin': 'DEL',
    'destination': 'BLR',
    'cabin_class': 'Y',
    'amount_raw': -8000.00,  # Negative amount!
    'currency': 'INR'
})

# FLAG 5: FX Rate Missing (1 row) - Exotic currency
acme_travel_data.append({
    'trip_id': f'TRIP{random.randint(10000, 99999)}',
    'employee_id': f'EMP{random.randint(1000, 9999)}',
    'department': 'Sales',
    'cost_center': 'CC-100',
    'expense_date': '2024-01-25',
    'mode': 'AIR',
    'origin': 'BOM',
    'destination': 'SIN',
    'cabin_class': 'Y',
    'amount_raw': 1500.00,
    'currency': 'ZAR'  # South African Rand - not in currency table
})

df_acme_travel = pd.DataFrame(acme_travel_data)
df_acme_travel.to_csv('sample_uploads/ACME_TRAVEL_JAN2024.csv', index=False)
print(f"[OK] ACME_TRAVEL_JAN2024.csv ({len(acme_travel_data)} rows)")
print("     - 10 clean rows")
print("     - 2 unknown_airport")
print("     - 1 missing_airport")
print("     - 1 unknown_cabin_class")
print("     - 1 negative_amount")
print("     - 1 fx_rate_missing")
print()

# ============================================================================
# TECHCORP INDUSTRIES - Similar flags for variety
# ============================================================================

# TechCorp SAP (simplified, similar flags)
tech_sap_data = []
materials = [
    ('200001', 'Diesel - Industrial Grade', 'DIESEL', 'BLR-001'),
    ('200002', 'Petrol - Premium', 'PETROL', 'BLR-001'),
]

# 12 clean + 3 unknown_plant + 2 negative + 1 unknown_material
for i in range(12):
    material = random.choice(materials)
    tech_sap_data.append({
        'MATNR': material[0],
        'MAKTX': material[1],
        'MATKL': material[2],
        'WERKS': material[3],
        'BUDAT': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
        'MENGE': round(random.uniform(100, 800), 2),
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'VEN{random.randint(1000, 9999)}',
        'EBELN': f'PO-TECH-{random.randint(10000, 99999)}'
    })

# Unknown plant
for i in range(3):
    tech_sap_data.append({
        'MATNR': '200001',
        'MAKTX': 'Diesel - Industrial Grade',
        'MATKL': 'DIESEL',
        'WERKS': 'UNKNOWN-PLANT',
        'BUDAT': (base_date + timedelta(days=12+i)).strftime('%Y-%m-%d'),
        'MENGE': round(random.uniform(100, 800), 2),
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'VEN{random.randint(1000, 9999)}',
        'EBELN': f'PO-TECH-{random.randint(10000, 99999)}'
    })

# Negative quantity
for i in range(2):
    tech_sap_data.append({
        'MATNR': '200001',
        'MAKTX': 'Diesel - Industrial Grade',
        'MATKL': 'DIESEL',
        'WERKS': 'BLR-001',
        'BUDAT': (base_date + timedelta(days=15+i)).strftime('%Y-%m-%d'),
        'MENGE': -round(random.uniform(50, 150), 2),
        'MEINS': 'L',
        'BWART': '101',
        'LIFNR': f'VEN{random.randint(1000, 9999)}',
        'EBELN': f'PO-TECH-{random.randint(10000, 99999)}'
    })

# Unknown material
tech_sap_data.append({
    'MATNR': '299999',
    'MAKTX': 'Unknown Chemical',
    'MATKL': 'UNKNOWN',
    'WERKS': 'BLR-001',
    'BUDAT': '2024-01-20',
    'MENGE': 100.0,
    'MEINS': 'L',
    'BWART': '101',
    'LIFNR': 'VEN5555',
    'EBELN': 'PO-TECH-99999'
})

df_tech_sap = pd.DataFrame(tech_sap_data)
df_tech_sap.to_csv('sample_uploads/TECHCORP_SAP_MB51_JAN2024.csv', index=False)
print(f"[OK] TECHCORP_SAP_MB51_JAN2024.csv ({len(tech_sap_data)} rows)")
print("     - 12 clean, 3 unknown_plant, 2 negative_quantity, 1 unknown_material")
print()

# TechCorp Utility (4 clean + 2 unknown + 1 negative)
tech_utility_data = []
for i in range(4):
    tech_utility_data.append({
        'service_number': 'KA-METER-100' if i < 2 else 'TN-METER-200',
        'tariff_category': 'HT-2',
        'from_date': (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=i*30 + 28)).strftime('%Y-%m-%d'),
        'units': random.randint(8000, 20000),
        'unit': 'kWh',
        'amount': round(random.uniform(80000, 200000), 2)
    })

# Unknown meter
for i in range(2):
    tech_utility_data.append({
        'service_number': 'UNKNOWN-MTR',
        'tariff_category': 'HT-2',
        'from_date': (base_date + timedelta(days=120+i*30)).strftime('%Y-%m-%d'),
        'to_date': (base_date + timedelta(days=120+i*30 + 28)).strftime('%Y-%m-%d'),
        'units': random.randint(8000, 20000),
        'unit': 'kWh',
        'amount': round(random.uniform(80000, 200000), 2)
    })

# Negative
tech_utility_data.append({
    'service_number': 'KA-METER-100',
    'tariff_category': 'HT-2',
    'from_date': '2024-01-20',
    'to_date': '2024-02-18',
    'units': -10000,
    'unit': 'kWh',
    'amount': round(random.uniform(80000, 200000), 2)
})

df_tech_utility = pd.DataFrame(tech_utility_data)
df_tech_utility.to_csv('sample_uploads/TECHCORP_ELECTRICITY_JAN2024.csv', index=False)
print(f"[OK] TECHCORP_ELECTRICITY_JAN2024.csv ({len(tech_utility_data)} rows)")
print("     - 4 clean, 2 unknown_meter, 1 negative_consumption")
print()

# TechCorp Travel (8 clean + 2 unknown airport + 1 missing FX)
tech_travel_data = []
for i in range(8):
    route = ('BLR', 'DEL')
    tech_travel_data.append({
        'trip_id': f'TECH-{random.randint(1000, 9999)}',
        'employee_id': f'TECH-EMP{random.randint(100, 999)}',
        'department': random.choice(['Engineering', 'Product']),
        'cost_center': 'TECH-100',
        'expense_date': (base_date + timedelta(days=i*2)).strftime('%Y-%m-%d'),
        'mode': 'AIR',
        'origin': 'BLR',
        'destination': 'DEL',
        'cabin_class': 'Y',
        'amount_raw': round(random.uniform(4000, 15000), 2),
        'currency': 'INR'
    })

# Unknown airport
for i in range(2):
    tech_travel_data.append({
        'trip_id': f'TECH-{random.randint(1000, 9999)}',
        'employee_id': f'TECH-EMP{random.randint(100, 999)}',
        'department': 'Sales',
        'cost_center': 'TECH-200',
        'expense_date': (base_date + timedelta(days=16+i)).strftime('%Y-%m-%d'),
        'mode': 'AIR',
        'origin': 'BLR',
        'destination': 'ABC',  # Unknown
        'cabin_class': 'Y',
        'amount_raw': round(random.uniform(5000, 15000), 2),
        'currency': 'INR'
    })

# Missing FX rate
tech_travel_data.append({
    'trip_id': f'TECH-{random.randint(1000, 9999)}',
    'employee_id': f'TECH-EMP{random.randint(100, 999)}',
    'department': 'Engineering',
    'cost_center': 'TECH-100',
    'expense_date': '2024-01-20',
    'mode': 'AIR',
    'origin': 'BLR',
    'destination': 'NRT',
    'cabin_class': 'Y',
    'amount_raw': 120000.00,
    'currency': 'JPY'  # Japanese Yen - not in currency table
})

df_tech_travel = pd.DataFrame(tech_travel_data)
df_tech_travel.to_csv('sample_uploads/TECHCORP_TRAVEL_JAN2024.csv', index=False)
print(f"[OK] TECHCORP_TRAVEL_JAN2024.csv ({len(tech_travel_data)} rows)")
print("     - 8 clean, 2 unknown_airport, 1 fx_rate_missing")
print()

print("=" * 60)
print("[SUCCESS] All flagged demonstration files created!")
print("=" * 60)
print()
print("SUMMARY:")
print(f"  Total Acme rows: {len(acme_sap_data) + len(acme_utility_data) + len(acme_travel_data)}")
print(f"  Total TechCorp rows: {len(tech_sap_data) + len(tech_utility_data) + len(tech_travel_data)}")
print()
print("Expected flags in Review Queue:")
print("  - unknown_plant")
print("  - unknown_material")
print("  - negative_quantity / negative_consumption / negative_amount")
print("  - duplicate_row")
print("  - unit_inconsistency / unit_ambiguous")
print("  - unknown_airport / missing_airport")
print("  - unknown_cabin_class")
print("  - fx_rate_missing")
print()
