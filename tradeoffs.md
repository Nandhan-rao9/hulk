# TRADEOFFS.md

Three things I deliberately did NOT build and why.

---

## 1. Complicated movement of goods in SAP, great circle distance calculation for flights.

**Did NOT Build:**
- return of goods (BWART 122), transfers (BWART 311) in SAP
- re-estimating flight paths and stalls for more accurate emissions


**Why:**
- resorted to simple rule-based calculations for demo instead of trying to build complex models that take into account all the factors for demo.
- re-estimating flight paths and stalls would require complex geospatial calculations and access to detailed flight data.

**What would be needed for production:**
- for SAP: handling returns and transfers would require additional logic to correctly account for the movement of goods and avoid double counting emissions.
- for flights: integrating with a geospatial service, having detailed information about flight routes and airports.

---

## 2. PDF Bill Parsing

**Did NOT Build:**
- OCR / PDF parsing for utility bills
- Manual correction workflow for OCR errors

**Why:**
- can get messy, especially with different bill formats and potential for low accuracy. For demo, focused on structured CSV input.

---

---

## 3. GEN-AI integration 
**Did NOT Build:**
- Gen-AI for normalisation of unknown units and column headers, complex emission calculations, re estimating flight paths and stalls, complex hotel stay calculations, complex car rental calculations, etc.

---

## 4. Soft Deletes. row level locking

**Did NOT Build:**
- `is_deleted` flag with archive
- S3 backup before deletion
- Admin recovery interface
- row level locking for audit log after approved.


**What would be needed for production:**
- would be good if the files are accidentally deleted, and there is a copy in S3 that can be restored.
- row level locking would be needed to prevent concurrent edits and ensure data integrity in the audit log, especially after approval when records should be immutable.
---

**End of TRADEOFFS.md**
