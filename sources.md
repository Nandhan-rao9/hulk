# SOURCES.md

This document details the real-world formats I researched, what I learned, how my sample data reflects reality, and what would break in production.

---

## 1. SAP - Fuel and Procurement Data

### Real-World Format Researched

**Format:** MB51 Material Document List (Transaction Code: MB51)  
**Export Type:** Flat CSV export via SAP GUI

**What I Learned:**

SAP MB51 is the standard transaction for material document reporting in SAP ECC and S/4HANA. After researching SAP documentation and community forums, I discovered:

1. **Transaction Code MB51** generates material movement reports (Goods Receipts 101, Goods Issues 261, Returns 122, etc.)

2. **Header Variations Are Common:**
   - **German headers** appear in German-localized SAP systems: 
   - **Mixed headers** in partially localized systems (German field codes like WERKS but English descriptions)

3. **Unit Inconsistency:**
   - Same material can appear in different units across purchases (Diesel in L vs GAL)
   - Energy can be recorded as volume (M3 for natural gas) OR as converted energy (KWH)
   - This creates classification ambiguity (is M3 referring to natural gas or diesel?)

4. **Decimal Format Hell:**
   - German systems export: `5.000,50` (5000.5 liters)
   - English systems export: `5,000.50` (5000.5 liters)
   - Parser must handle both formats (I used regex detection: if `,` appears before `.`, it's German)

- SAP Community Thread: (https://community.sap.com/t5/enterprise-resource-planning-q-a/mb51/qaq-p/8735458)
- MB51 (https://www.linkedin.com/posts/surya-prakash1123_sapmm-mb51-saptraining-share-7335584437251788801-QP_N/)

---

### Sample Data Rationale


**Why It Looks This Way:**

I designed the sample to test every edge case I discovered in research:

#### Row-by-Row Breakdown:

**Row 1-2:** Same diesel material (MAT-10234) in different units (L vs GAL)
- **Why:** Tests unit normalization (GAL → L conversion factor 3.785411)
- **Real-world case:** Vendor A sells diesel in liters, Vendor B in gallons

**Row 3:** Petrol (Unleaded 95 Octane)
- **Why:** Tests multi-fuel classification (not just diesel)
- **MATKL code:** FUEL-LQ (Liquid Fuels category)

**Row 4:** Natural gas with **plant code XX99** (unknown plant)
- **Why:** Tests plant lookup failure → should flag `unknown_plant`
- **Real-world case:** Client forgets to seed plant lookup table, or new plant not configured

**Row 5:** LPG in KG (solid unit)
- **Why:** Tests unit diversity (not all fuels are liquid)
- **Real-world case:** LPG sold by weight in cylinders

**Row 6:** Diesel with **negative quantity** and **BWART 122** (return)
- **Why:** Tests exclusion logic (returns should NOT count as emissions)
- **Real-world case:** Defective fuel batch returned to vendor
- **Expected behavior:** Parser excludes via `exclude_reason='BWART=122 return'`

**Row 7:** Furnace oil (heavy fuel oil)
- **Why:** Tests industrial fuel classification (not just transport fuels)

**Row 8:** Coal in KG (15000 KG = 15 metric tons)
- **Why:** Tests solid fuel classification
- **MATKL code:** COAL-BIT (Coal Bituminous category)

**Row 9:** Aviation fuel (ATF/Jet fuel)
- **Why:** Tests kerosene-based fuels
- **Scope:** Should be Scope 1 (direct company aircraft) or Scope 3 (leased aircraft)

**Row 10:** Electrical energy in KWH
- **Why:** Tests electricity procurement via SAP (some companies buy power as "material")
- **Edge case:** Should this be Scope 2? Parser handles via ELEC-GR material group.

**Row 11:** Unknown material with **missing MATKL code**
- **Why:** Tests fallback classification (should use keyword matching on material description "Unknown Material XYZ-445")
- **Expected behavior:** Flag `unclassified` if no match

**Row 12-13:** **Exact duplicate** (same date, plant, material, quantity, PO)
- **Why:** Tests duplicate detection (SHA256 hash of row)
- **Real-world case:** User accidentally uploads same file twice, or SAP export glitches
- **Expected behavior:** Flag `duplicate_row` on row 13

**Row 14:** Diesel in GAL at new plant 1005
- **Why:** Tests multi-plant scenario

**Row 15:** Petrol in **KG** (wrong unit for liquid)
- **Why:** Tests unit inconsistency detection (petrol should be L or GAL, not KG)
- **Expected behavior:** Flag `inconsistent_unit`

**Row 16:** Natural gas in **KWH** (converted energy unit)
- **Why:** Tests ambiguity (M3 is volumetric, KWH is energy. Both valid but represent different measurement stages)
- **Expected behavior:** Flag `inconsistent_unit` or accept if emission factor matches

**Row 17:** Cutting oil (non-fuel material)
- **Why:** Tests unclassified material (no emission factor exists)
- **Expected behavior:** Flag `unclassified` and status=FLAGGED

**Row 18:** LPG in **L** (volume instead of weight)
- **Why:** Tests unit variation for same fuel type


---

### What Would Break in Production

#### 1. **Format Limitations**
- **Only supports CSV flat file export** - No support for:
  - IDoc (Intermediate Document) format for SAP-to-SAP integration
  - OData/REST API from S/4HANA
  - BAPI (Business API) RFC calls for real-time data pull

#### 2. **Plant Lookup Dependency**
- **Pre-seeding required:** Client must manually create plant_lookups mapping (WERKS code → facility_id)
- **Example:** WERKS 1001 → "Chennai Plant", WERKS 1002 → "Mumbai Plant"
- **Real-world problem:** New plants added in SAP mid-year won't auto-appear in emissions platform

#### 3. **Material Group Mapping is Client-Specific**
- **No universal standard:** MATKL codes vary by client:
  - Client A uses `FUEL-LQ` for diesel
  - Client B uses `MAT-001` for diesel
  - Client C uses `KRAFTSTOFF-DIESEL` for diesel
- **Pre-configuration required:** Admin must seed `client_material_group_mappings` table per org
- **Fallback exists:** Keyword matching on material description (but less accurate)

#### 4. **No Support for Batch/Partial Files**
- Current implementation processes full file or fails
- **Real-world need:** Large clients may have 100k+ rows/month. Need chunked processing or streaming parser.

#### 5. **Movement Type Simplification**
- Only handles BWART 101 (Goods Receipt) vs 122 (Return)
- **Missing:** 261 (Goods Issue), 311 (Transfer Posting), 551 (Stock Withdrawal)
- **Real-world:** Manufacturing plants may issue fuel to cost centers (261) - need logic to avoid double-counting

---

## 2. Utility - Electricity Data

### Real-World Format Researched

**Format:** TSSPDCL Portal CSV Export  
**Source:** Telangana State Southern Power Distribution Company Limited (India)

**What I Learned:**

Indian electricity distribution is state-level. Each state has DISCOMs (Distribution Companies) that manage retail supply to consumers. I researched TSSPDCL as a representative example.

1. **TSSPDCL Portal Export Format:**
   - Available at: https://portal.tssouthernpower.com/ (requires login)
   - Customers can download billing history as CSV (Service Number, Period, Units, Tariff, Amount)
   - Format is semi-standardized (other DISCOMs like MSEDCL, BESCOM, APSPDCL have similar structures)

2. **Tariff Categories:**
   - **HT (High Tension)** - Industrial consumers (>11 kV supply)
     - HT-1: General Industries
     - HT-2: Heavy Industries (steel, cement, chemical)
   - **LT (Low Tension)** - Commercial/small industry (<1 kV)
     - LT-3: Non-domestic (commercial)
     - LT-1: Domestic (residential)
   - **Tariff determines pricing** but NOT emission factor (all grid electricity has same factor)


3. **Unit Ambiguity:**
   - Standard unit: `kWh` (kilowatt-hours) = energy consumed
   - Edge case: `kVAh` (kilovolt-ampere-hours) = apparent energy (includes reactive power)
   - **Problem:** kVAh ≠ kWh. Using wrong unit inflates emissions.
   - **Solution:** Flag `unit_ambiguity` if kVAh detected

4. **CEA Emission Factor (India Grid):**
   - CEA = Central Electricity Authority of India
   - Publishes annual "CO2 Baseline Database for Indian Power Sector"
   - **2023-24 Factor:** 0.716 kgCO2e/kWh (all-India grid average)
   - Source: https://cea.nic.in/baseline-carbon-dioxide-emissions-database/
   - **State-specific factors exist** (e.g., Telangana 0.82 kgCO2e/kWh) but most companies use all-India average

5. **Meter Number as Plant Identifier:**
   - Service Number (e.g., 550012345) uniquely identifies a meter
   - One facility may have multiple meters (main plant, admin building, warehouse)
   - **Solution:** `plant_lookups` table maps service_no → facility_id

**Sources Consulted:**
- TSSPDCL Official Portal: https://portal.tssouthernpower.com/
- CEA CO2 Baseline Database 2023-24: https://cea.nic.in/wp-content/uploads/baseline/2024/01/Approved_Report_2023_24.pdf

---

### Sample Data Rationale

**File:** `sample_data/tsspdcl_utility.csv`

**Why It Looks This Way:**

#### Row-by-Row Breakdown:

**Row 1-2:** Service 550012345 - consecutive months (Jan 5-Feb 3, Feb 3-Mar 5)
- **Why:** Tests normal billing sequence
- **Tariff:** HT-1 (General Industry)

**Row 3-4:** Service 550012346 - consecutive months (Jan 8-Feb 8, Feb 8-Mar 8)
- **Why:** Tests different tariff (HT-2 Heavy Industry)

**Row 5:** Service 550012347 - Jan 12 to Feb 10
- **Why:** Normal bill
- **Tariff:** LT-3 (Commercial)

**Row 6:** Service 550012347 - **Gap: Feb 10 to Apr 15** (64 days)
- **Why:** Tests gap detection (>35 days between bills)
- **Real-world case:** Meter malfunction, billing cycle skipped, estimated bill later
- **Expected behavior:** Flag `long_gap` (suspicious, may indicate missing data)

**Row 7:** Service **UNKNOWN-9999** (unknown meter)
- **Why:** Tests facility lookup failure
- **Real-world case:** New meter installed, not yet added to plant_lookups table
- **Expected behavior:** Flag `unknown_plant`, facility_id=NULL

**Row 8-9:** Service 550012348 - consecutive months
- **Why:** Tests high consumption (15600 kWh, 16200 kWh) for large facility

---

### What Would Break in Production

#### 1. **PDF Bill Parsing Not Supported**
- Many DISCOMs don't offer CSV export, only PDF bills
- **Real need:** OCR-based extraction from PDF (libraries: Tesseract, AWS Textract, Google Vision API)
- **Complexity:** PDF layouts vary by DISCOM and change over time

#### 2. **Only TSSPDCL Format Supported**
- Each DISCOM has slightly different CSV schema:
  - MSEDCL (Maharashtra) uses "Consumer No" instead of "Service No"
  - BESCOM (Bangalore) includes demand charges in separate columns
  - APSPDCL (Andhra Pradesh) has different tariff codes (LT-I, LT-II instead of LT-1, LT-2)
- **Needed:** Parser registry pattern with per-DISCOM parsers

#### 3. **No API Integration with Utility Portals**
- Some utilities offer APIs (e.g., BESCOM has unofficial API)
- **Real-world value:** Auto-sync billing data monthly instead of manual upload
- **Challenge:** Most Indian DISCOMs don't have public APIs, require screen scraping (breaks frequently)

#### 4. **Demand Charges Ignored**
- HT consumers pay for both:
  - **Energy charges** (kWh consumed)
  - **Demand charges** (kVA peak demand)
- Demand charges don't affect emissions (same kWh), but needed for cost allocation
- **Current implementation:** Only tracks kWh, ignores rupee amounts

#### 5. **Power Factor Adjustments Not Handled**
- Low power factor (reactive power) results in:
  - Higher kVAh than kWh
  - Financial penalties from DISCOM
- **Emissions impact:** Should use kWh (real energy), not kVAh
- **Current workaround:** Flag kVAh as ambiguous, analyst decides

#### 6. **No Support for Solar/Renewable Offsets**
- Many Indian factories have rooftop solar (net metering)
- Bill shows:
  - Grid import (kWh drawn)
  - Solar export (kWh supplied to grid)
  - Net consumption (import - export)
- **Current parser:** Assumes `units_kwh` is gross consumption, doesn't account for solar offset
- **Needed:** Separate columns for import/export, or flag net-metered facilities

#### 7. **State-Specific Emission Factors Not Used**
- Current implementation uses all-India factor (0.716 kgCO2e/kWh)
- **More accurate:** State-level factors (Telangana 0.82, Karnataka 0.71, Tamil Nadu 0.68)
- **Reason for all-India factor:** Simplicity, consistency across multi-state orgs
- **Production upgrade:** Add state field to facilities table, use state-specific CEA factors

---

## 3. Corporate Travel - Flights, Hotels, Ground Transport

### Real-World Format Researched

**Formats:** Concur Expense Reports + Navan Booking Reports  
**Focus:** CSV exports from expense management and travel booking platforms

**What I Learned:**

Corporate travel data lives in two types of systems:

#### A. Expense Management Systems (Concur, Expensify, Zoho Expense)
**Example: SAP Concur Expense Reports**
- CSV export from Concur Standard or Concur Expense
- Available at: https://www.concur.com/en-us/expense-management
- Contains: Employee ID, Department, Travel Date, Expense Type (Airfare, Hotel, Car Rental), Amount, Currency, Origin/Destination (if flight)

**What I Learned:**
1. **I used, Expense-focused, not emission-focused:**
   - Primary data: Dollar amount spent
   - Secondary data: Flight route (sometimes), hotel nights (sometimes)
   - Missing: Distance (must calculate from airport codes), cabin class (often missing)

2. **Cabin Class Encoding Hell:**
   - Airlines use **booking class codes** (Y, B, M, H, Q, W = Economy; J, C, D, I = Business; F, A = First)
   - Concur sometimes captures raw code (Y, J), sometimes normalized label (Economy, Business)
   - **Problem:** Y-class can be economy on international flights, premium economy on domestic
   - **Solution:** Map common codes (Y/B/M/H → ECONOMY, J/C/D → BUSINESS, F/A → FIRST), flag unknowns

3. **Currency Conversion Required:**
   - Travel expenses in multiple currencies (USD, EUR, GBP, SGD for international trips)
   - **Current implementation:** Uses `currency_conversion_rates` table (INR as base)
   - **Real-world:** Exchange rates change daily, need dated FX rates (not static)

#### B. Travel Booking Systems (Navan, TripActions, Deem)
**Example: Navan Booking Reports**
- CSV export from Navan dashboard
- Available at: https://www.navan.com/ (formerly TripActions)
- Contains: Trip ID, Employee, Origin/Destination IATA codes, Carrier, Cabin Class, Cost, Booking Date

**What I Learned:**
1. **Booking-focused, more structured:**
   - Primary data: Flight route (IATA codes like DEL, BOM, SIN, LHR)
   - Distance NOT provided → must calculate using great circle formula
   - Cabin class labeled (Economy, Premium Economy, Business, First)

2. **Trip Grouping:**
   - One business trip = multiple rows:
     - Outbound flight (HYD → DEL)
     - Hotel (3 nights)
     - Return flight (DEL → HYD)
   - **Solution:** `trip_id` groups related expenses, allows "trip-level" emissions reporting

3. **Hotel Location Often Missing:**
   - Hotels don't have standardized location codes (unlike IATA for airports)
   - **Problem:** Hotel emissions vary by city (London hotel ≠ Delhi hotel due to grid factors)
   - **Workaround:** Use spend-based factor (INR spent × spend-based emission factor per night)

4. **IATA Airport Database:**
   - 3-letter codes from International Air Transport Association
   - **Common Indian airports:** DEL (Delhi), BOM (Mumbai), BLR (Bangalore), HYD (Hyderabad), CCU (Kolkata), MAA (Chennai)
   - **International:** SIN (Singapore), LHR (London), DXB (Dubai), JFK (New York)
   - **Database:** Seeded ~100 airports with lat/long for distance calculation

5. **Great Circle Distance Formula:**
   - Haversine formula calculates straight-line distance between two lat/long points
   - **Formula:** `d = 2r × arcsin(sqrt(sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlong/2)))`
   - Where `r = 6371 km` (Earth radius)
   - **Accuracy:** Within 1-2% of actual flight path (which follows air routes, not straight line)
   - **Alternative:** Actual flight distance APIs (FlightAware, FlightRadar24) - not implemented due to API cost

6. **DEFRA 2024 Emission Factors (UK Government):**
   - DEFRA = Department for Environment, Food & Rural Affairs (UK)
   - Publishes annual GHG conversion factors: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
   - **Flight factors vary by:**
     - **Distance band:** Short-haul (<500 km), Medium (500-3700 km), Long (>3700 km)
     - **Cabin class:** Economy, Premium Economy, Business, First
     - **With/without Radiative Forcing (RF):** RFI factor 1.9× (accounts for high-altitude contrails)
   - **My implementation:** Used per-km factors for simplicity:
     - Economy: 0.15 kgCO2e/km
     - Business: 0.23 kgCO2e/km
     - First: 0.30 kgCO2e/km
   - **Hotel factor:** 30 kgCO2e/night (average, varies by country/star-rating)
   - **Car rental:** 0.17 kgCO2e/km (average sedan, spend-based fallback if distance unknown)

**Sources Consulted:**
- SAP Concur Developer Center: https://developer.concur.com/api-reference/
- Navan (TripActions) Export Documentation: https://navan.com/resources/
- DEFRA GHG Conversion Factors 2024: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- IATA Airport Codes: https://www.iata.org/en/publications/directories/code-search/
- Great Circle Mapper (for validation): http://www.gcmap.com/
- Academic papers on aviation emissions (Radiative Forcing Index)

---

### Sample Data Rationale

**File:** `sample_data/concur_travel.csv`

**Why It Looks This Way:**

#### Trip-by-Trip Breakdown:

**TRIP-2401-001 (Employee EMP-1234, Sales):**
- Row 1: AIR HYD → DEL, Economy (domestic short-haul ~1300 km)
- Row 2: HOTEL 3 nights in Delhi
- Row 3: AIR DEL → HYD, Economy (return flight)
- **Why:** Tests typical business trip grouping (outbound + hotel + return)
- **Purpose:** Sales meeting in Delhi

**TRIP-2401-002 (Employee EMP-2345, Engineering):**
- Row 4: AIR BLR → BOM, Business class (domestic ~850 km)
- Row 5: HOTEL 2 nights in Mumbai
- Row 6: CAR (Uber, no distance given)
- Row 7: AIR BOM → BLR, Business (return)
- **Why:** Tests business class (higher emission factor 0.23 vs 0.15 kgCO2e/km)
- **Why CAR:** Tests ground transport with spend-based fallback (no km provided)

**TRIP-2401-003 (Employee EMP-3456, Finance):**
- Row 8: AIR HYD → BLR, cabin class **"Y"** (raw booking code)
- Row 9: HOTEL 1 night
- Row 10: AIR BLR → HYD, cabin class **"Y"**
- **Why:** Tests cabin class normalization (Y → ECONOMY)
- **Real-world case:** Concur exports raw airline booking codes

**TRIP-2401-004 (Employee EMP-4567, Operations):**
- Row 11: AIR **origin missing** → SIN (Singapore), cabin class **"J"** (business)
- Row 12: HOTEL 4 nights (Marina Bay Sands, expensive)
- Row 13: AIR SIN → HYD, cabin class **"J"**
- **Why:** Tests international travel (long-haul >3000 km)
- **Why missing origin:** Tests flag `missing_airport_code` (can't calculate distance without origin)
- **Why J-class:** Tests cabin class code normalization (J → BUSINESS)


---

### What Would Break in Production
- current implementation handles basic cases but lacks support for many real-world complexities. The following features
   - not wide enough Airport database (only seeded 100 major airports, but many trips may involve smaller regional airports)
   - no support for rail travel (e.g., Delhi → Agra by train)
   - columns missing that may appear in real-world data

would be nice to implement - 
#### 1. **API Pull Not Implemented (File Upload Only)**
- **Real need:** Daily/weekly auto-sync from Concur/Navan via API
- **Zoho Expense:** Indian platform, INR-focused 
      - should be implemented to capture local market share

#### 2. **No Rail Route Database**
- Flights: IATA codes standardized, airport lat/long available
- **Rail:** No equivalent global standard

#### 3. **No Hotel Location Emissions (City-Specific Factors)**
- **Current:** Generic 30 kgCO2e/night (DEFRA average)
- **More accurate:** Vary by city grid emission factor:
  - London hotel: 0.23 kgCO2e/kWh (UK grid) × 50 kWh/night = 11.5 kgCO2e
  - Delhi hotel: 0.82 kgCO2e/kWh (India grid) × 50 kWh/night = 41 kgCO2e

#### 4. **Multi-Leg Flights Not Handled**
- **Real-world:** HYD → DEL → LHR (1 stop in Delhi)
- **Current parser:** Treats as single flight HYD → LHR (great circle = 6700 km)
- **Actual flight path:** HYD → DEL (1300 km) + DEL → LHR (6700 km) = 8000 km
- **Needed:** Leg-by-leg tracking (requires booking details, not just expense report)

---

## Emission Factors - Sources and Validation

### DEFRA 2024 (UK Government)

**Source:** https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024  
