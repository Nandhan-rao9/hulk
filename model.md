# HULK - Data Model

## Overview

This is a multi-tenant emissions tracking platform that ingests data from three sources (SAP, utility bills, travel platforms), normalizes it into a canonical format, and provides a two-stage approval workflow (analyst → admin) for audit compliance.

**Database:** PostgreSQL (production) / SQLite (dev)  
**Pattern:** Thin canonical table + source-specific detail tables  
**Tables:** 15 custom tables across 4 Django apps

---

## Core Design Principles

### 1. Multi-Tenancy
Every record is scoped to an `organization`. Users belong to one org, and all queries are automatically filtered by `org_id`. This allows multiple clients to use the same database with complete data isolation.

### 2. Immutable Source Data
When a CSV is uploaded, we store the original row in `raw_records` as JSON. This table is never edited or deleted (except cascade when the parent file is deleted). This gives us a permanent audit trail of what was actually uploaded.

### 3. Thin Canonical Table Pattern
Instead of cramming all fields into one giant table (which would be 90% NULL), we split data into:
- **activities** - common fields (scope, category, period, status)
- **sap_details**, **utility_details**, **travel_details** - source-specific fields

This makes queries cleaner (you JOIN only what you need) and makes it easy to add new source types.

### 4. Two-Stage Approval Workflow
```
FLAGGED → (analyst reviews) → PENDING → (admin approves) → APPROVED
```

This implements the "two pairs of eyes" principle for audit compliance. Analysts review suspicious data, admins give final sign-off.

---

## Database Schema

### Core App - Master Data

#### **organizations**
Multi-tenancy root. Every record in the system belongs to one org.

```
id, name, slug, created_at
```

---

#### **users**
Custom user model extending Django's AbstractUser. Added fields:
- `org_id` - which organization they belong to
- `role` - either 'analyst' or 'admin'

Analysts can review and send activities for approval. Admins can give final approval and delete files.

---

#### **facilities**
Physical locations the client operates (plants, offices, warehouses).

```
id, org_id, name, city, country, created_at
UNIQUE(org_id, name)
```

---

#### **plant_lookups**
Maps opaque codes from source files to actual facilities.

```
id, org_id, facility_id, source_type, code
UNIQUE(org_id, source_type, code)
```

**Example:** SAP plant code "1000" maps to facility "Chennai Plant"

**Why this exists:** SAP exports contain plant codes like "1000" or "2000" which mean nothing without a lookup table. Same with utility meter numbers.

---

#### **client_material_group_mappings**
Maps SAP material group codes (MATKL) to fuel types.

```
id, org_id, matkl_code, fuel_type, scope, created_at
UNIQUE(org_id, matkl_code)
```

**Example:** MATKL="MAT01" → fuel_type="DIESEL", scope=1

**Why this exists:** SAP doesn't label diesel as "diesel" - it uses material group codes. Each client has different codes, so this is a per-org mapping table.

---

#### **emission_factors**
Global table of emission factors from DEFRA 2024 and CEA 2023-24. Seeded once, never mutated.

```
id, fuel_type, unit, factor_kgco2e, source, year, notes
UNIQUE(fuel_type)
```

**Example:** 
- DIESEL: 2.687 kgCO2e/L (DEFRA 2024)
- ELECTRICITY (India grid): 0.72 kgCO2e/kWh (CEA 2024)

---

#### **currency_conversion_rates**
Currency conversion rates to INR for travel expense data.

```
id, currency_code, rate_to_inr, effective_date, source, updated_at
UNIQUE(currency_code)
```

---

#### **reporting_period_locks**
Tracks which months are locked for reporting. Once locked, no edits allowed.

```
id, org_id, period_month, locked_by, locked_at, is_locked, unlocked_by, unlocked_at, unlock_reason
UNIQUE(org_id, period_month)
```

**Why this exists:** Audit compliance. Once a month is reported to auditors, you can't go back and change the data.

---

### Ingestion App - File Upload & Raw Data

#### **source_files**
Tracks uploaded CSV files.

```
id, org_id, source_type, original_filename, file_hash, uploaded_by_id, uploaded_at, 
status, total_rows, failed_rows, flagged_rows, pending_rows, approved_rows
UNIQUE(org_id, file_hash)
```

**Counters:** We denormalize row counts (flagged_rows, pending_rows, etc.) for performance. The UI needs these instantly for file cards, and running COUNT(*) on large tables would be slow.

**Duplicate Detection:** SHA256 hash prevents uploading the same file twice.

---

#### **raw_records**
Immutable snapshot of each CSV row.

```
id, source_file_id, row_number, raw_data (JSON), ingested_at, parse_status, parse_error, exclude_reason
```

**Why JSON?** Different sources have different columns. SAP has MATNR/MATKL/WERKS, utility has meter numbers, travel has cabin class. We store the raw dict so we can always trace back to the original data.

**Immutability:** Policy is never edit/delete. Enforced by team discipline (not DB constraints) for dev flexibility.

---

### Activities App - Canonical Emissions Data

#### **activities**
The thin canonical table. One activity per CSV row that passes parsing.

```
id, org_id, source_file_id, raw_record_id, facility_id, scope, category, 
period_start, period_end, emissions_kgco2e, status, is_suspicious, flag_reason, 
is_cross_month, approved_by_id, approved_at, created_at
```

**Key Fields:**
- `scope` - 1, 2, or 3 (emissions classification)
- `category` - DIESEL, ELECTRICITY, FLIGHT, HOTEL, etc.
- `period_end` - the date used for month locking checks
- `status` - FLAGGED, PENDING, APPROVED, LOCKED, INVALIDATED
- `flag_reason` - pipe-delimited flags like "unknown_plant|negative_quantity"

**Indexes:** 
- `(org_id, status)` - for review queues
- `(org_id, period_end)` - for monthly reports
- `(facility_id, period_end)` - for facility-level reports

---

#### **sap_details**
One-to-one with Activity. SAP-specific fields.

```
activity_id (PK), plant_code, material_number, material_desc, material_group,
quantity_raw, unit_raw, quantity_normalized, unit_normalized, 
conversion_factor, conversion_note, movement_type, vendor_number, po_number, classification_method
```

**Unit Normalization:** We convert everything to canonical units (gallons → liters, pounds → kg). Store both raw and normalized values so we can audit the conversion.

**Classification Method:** Tracks how we figured out the fuel type (MATKL code, keyword match, unit inference, manual, or unclassified).

---

#### **utility_details**
One-to-one with Activity. Utility-specific fields.

```
activity_id (PK), service_number, tariff_category, kwh_consumed, unit_raw,
billing_amount_inr, grid_emission_factor, emission_factor_source
```

---

#### **travel_details**
One-to-one with Activity. Travel-specific fields.

```
activity_id (PK), trip_id, employee_id, department, cost_center, mode,
origin, destination, distance_km, cabin_class, cabin_class_raw, nights,
amount_raw, currency, amount_inr, fx_rate_used, fx_rate_date, fx_source, fx_note, distance_method
```

**Mode:** AIR, HOTEL, CAR, RAIL

---

### Audit App - Compliance Trail

#### **audit_logs**
Append-only log of every state change. Never deleted.

```
id, activity_id, activity_snapshot (JSON), source_file_id, source_file_name, 
action, performed_by_id, performed_at, field_changed, old_value, new_value, note
```

**Key Innovation:** We use `SET_NULL` instead of `CASCADE` on foreign keys. Before the FK becomes NULL, we capture a JSON snapshot of the activity's state. This means even if data is deleted, we can prove what was approved.

**Example Snapshot:**
```json
{
  "id": 123,
  "category": "DIESEL",
  "scope": 1,
  "period_end": "2024-01-31",
  "facility_name": "Chennai Plant",
  "quantity": 1000,
  "unit": "L"
}
```

---

## Data Flow

### 1. File Upload

```
User uploads CSV 
  → Create source_files record (status=PROCESSING)
  → Parse each row → create raw_records (raw_data as JSON)
  → Transform each row:
       - Lookup facility via plant_lookups
       - Lookup fuel type via client_material_group_mappings
       - Normalize units (GAL→L, LBS→KG)
       - Check for flags (unknown plant? negative qty? suspicious pattern?)
  → Create activities record (status=FLAGGED or APPROVED)
  → Create detail record (sap_details / utility_details / travel_details)
  → Create audit_log (action=INGESTED)
  → Update source_files counters (flagged_rows, approved_rows)
  → Set status=DONE
```

---

### 2. Analyst Review

```
Analyst views FLAGGED queue
  → Clicks "Send for Approval" on activity
  → Check: is user an analyst? is period locked?
  → Update activity status: FLAGGED → PENDING
  → Create audit_log (action=REVIEWED)
  → Sync source_files counters (flagged_rows--, pending_rows++)
```

---

### 3. Admin Approval

```
Admin views PENDING queue
  → Clicks "Final Approve" on activity
  → Check: is user an admin? is period locked?
  → Update activity: status → APPROVED, approved_by_id, approved_at
  → Create audit_log (action=APPROVED)
  → Sync source_files counters (pending_rows--, approved_rows++)
```

---

### 4. File Deletion (Admin Only)

```
Admin deletes file
  → CASCADE DELETE raw_records
  → CASCADE DELETE activities
  → CASCADE DELETE sap_details / utility_details / travel_details
  → SET_NULL on audit_logs (but snapshot remains!)
```

**Why this is safe:** Audit logs preserve snapshots, so we can still show auditors what was approved even if the original data is gone.

---

## Key Trade-offs

### 1. Denormalized Counters
**Decision:** Store row counts in source_files instead of counting on-the-fly.

**Why:** Performance. The UI needs instant feedback. Running COUNT(*) on large activities table would be slow.

**Trade-off:** Must sync counters after every status change. Added complexity, but worth it for UX.

---

### 2. Soft Immutability
**Decision:** Policy to never edit/delete raw_records, but not enforced at DB level.

**Why:** Dev flexibility. In development, you want to delete test data. In production, you don't.

**Trade-off:** Relies on team discipline. Could harden with environment checks or DB triggers.

---

### 3. Separate Detail Tables
**Decision:** Split source-specific fields into sap_details, utility_details, travel_details instead of one big table.

**Why:** Avoid NULL hell. A SAP activity doesn't need cabin_class. A flight doesn't need plant_code.

**Trade-off:** More tables, more JOINs. But cleaner schema and easier to extend.

---

### 4. Period Locking
**Decision:** Lock entire months to prevent edits after reporting.

**Why:** Audit compliance. Once a month is finalized, you can't go back and change the data.

**Implementation:** Checked at workflow level (approve, flag, unflag methods).

---

## Multi-Tenancy

Every table has `org_id` foreign key (except global tables like emission_factors). Django middleware automatically filters queries by request.user.org.

**Security:** User can only see data from their own org. Admins can't delete other orgs' files.

**Scalability:** Single database for all clients. If one client gets huge, could shard by org_id later.

---

## Scope 1/2/3 Categorization

**Scope 1:** Direct emissions (diesel, petrol, natural gas burned on-site)  
**Scope 2:** Indirect emissions (purchased electricity)  
**Scope 3:** Other indirect (business travel, employee commute)

**How we determine scope:**
- **SAP:** From client_material_group_mappings (admin pre-configured MATKL → fuel type + scope)
- **Utility:** Always Scope 2 (purchased electricity)
- **Travel:** Always Scope 3 (business travel)

---

## Unit Normalization

**SAP data** comes in inconsistent units: gallons, liters, pounds, kg, cubic meters, therms.

**We normalize to:**
- Liquids → Liters (L)
- Gases → Cubic meters (M3)
- Solids → Kilograms (KG)
- Electricity → Kilowatt-hours (KWH)

**Store both:** `quantity_raw` + `unit_raw` (what was uploaded) and `quantity_normalized` + `unit_normalized` (what we use for emissions calc).

**Audit trail:** `conversion_factor` and `conversion_note` explain the conversion (e.g., "GAL→L: 3.785411").

---

## Source-of-Truth Tracking

Every activity points back to:
1. `source_file_id` - which file produced this row
2. `raw_record_id` - the exact CSV row (with original JSON)
3. `audit_logs` - every state change (who reviewed, who approved, when)

**If questioned:** "Where did this 1000L diesel entry come from?" → We can show:
- Original filename: ACME_SAP_JAN2024.csv
- Raw CSV row: {"MATNR": "123", "MENGE": "264.172", "MEINS": "GAL", "BUDAT": "20240115"}
- Transformation: 264.172 GAL → 1000 L (factor 3.785411)
- Who reviewed: John (analyst) on Jan 20
- Who approved: Sarah (admin) on Jan 22

---

## Audit Trail

**Three levels:**

1. **Immutable raw data:** raw_records never edited
2. **Activity snapshots:** audit_logs capture before-state on every change
3. **File metadata:** source_files track who uploaded, when, status

**Even if data is deleted:** Audit snapshots remain (via SET_NULL + JSON snapshot).

**Compliance:** Can prove to auditors what was approved, when, by whom, even months later.

---

## What This Doesn't Do (Yet)


- **Soft deletes** - We CASCADE delete instead of marking `is_deleted=True`. Could recover from mistakes with soft deletes + archive to S3.

- **Distance Calculation:** For flights, we calculate great circle distance from IATA codes. For hotels/cars, we use spend-based emission factors.


## Summary

This data model balances **audit compliance** (immutable source data, snapshots, two-stage approval) with **usability** (clean canonical table, performant counters, clear workflow states) while staying **extensible** (easy to add new source types via detail tables).

The core insight is the thin canonical table pattern: keep common fields (scope, period, status) in activities, put source-specific fields in detail tables. This avoids NULL hell and makes the schema easy to reason about.
