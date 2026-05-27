"""
SAP MB51 Material Document parser.

Handles:
- German header normalization (Buchungsdatum → BUDAT)
- Material classification waterfall (MATKL → keyword → unit → unclassified)
- Unit conversion (GAL→L, MT→KG)
- BWART filtering (101 only, all others excluded)
- Suspicious detection (unknown plant, negative qty, duplicates, etc.)
- German decimal format (1.234,56 → 1234.56)
"""
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from .base import BaseParser, ParseResult
from apps.activities.models import SAPDetail
from apps.core.models import PlantLookup, ClientMaterialGroupMapping


class SAPParser(BaseParser):
    """Parser for SAP MB51 material documents."""

    def __init__(self, org):
        """Initialize parser with org and duplicate tracking."""
        super().__init__(org)
        # Track row hashes within this file to detect duplicates
        self.seen_rows: Set[str] = set()

    # German → English header mapping (with common variants)
    GERMAN_HEADERS = {
        # Standard German headers
        'Buchungsdatum': 'BUDAT',
        'Werk': 'WERKS',
        'Materialnummer': 'MATNR',
        'Materialbezeichnung': 'MAKTX',
        'Materialgruppe': 'MATKL',
        'Menge': 'MENGE',
        'Mengeneinheit': 'MEINS',
        'Bewegungsart': 'BWART',
        'Lieferant': 'LIFNR',
        'Bestellnummer': 'EBELN',
        # English variants (with spaces/cases)
        'Posting Date': 'BUDAT',
        'Plant': 'WERKS',
        'Material': 'MATNR',
        'Material Number': 'MATNR',
        'Material Description': 'MAKTX',
        'Material Group': 'MATKL',
        'Quantity': 'MENGE',
        'Unit of Entry': 'MEINS',
        'Unit': 'MEINS',
        'Movement Type': 'BWART',
        'Vendor': 'LIFNR',
        'Purchase Order': 'EBELN',
        'PO Number': 'EBELN',
    }

    # Required headers (English names)
    REQUIRED_HEADERS = ['BUDAT', 'WERKS', 'MATNR', 'MAKTX', 'MENGE', 'MEINS', 'BWART']

    # Unit conversion factors
    UNIT_CONVERSIONS = {
        # Volume
        'GAL': ('L', Decimal('3.785411'), 'GAL->L: 3.785411'),
        'GALLON': ('L', Decimal('3.785411'), 'GALLON->L: 3.785411'),
        'LTR': ('L', Decimal('1.0'), 'LTR->L: 1.0'),
        'LIT': ('L', Decimal('1.0'), 'LIT->L: 1.0'),
        'LITER': ('L', Decimal('1.0'), 'LITER->L: 1.0'),

        # Mass
        'MT': ('KG', Decimal('1000.0'), 'MT->KG: 1000.0'),
        'T': ('KG', Decimal('1000.0'), 'T->KG: 1000.0'),
        'TON': ('KG', Decimal('1000.0'), 'TON->KG: 1000.0'),
        'TONNE': ('KG', Decimal('1000.0'), 'TONNE->KG: 1000.0'),

        # Energy
        'MWH': ('KWH', Decimal('1000.0'), 'MWH->KWH: 1000.0'),
        'MWHR': ('KWH', Decimal('1000.0'), 'MWHR->KWH: 1000.0'),
    }

    # Fuel type keywords (for fallback classification)
    # Include transliterations and common variants
    FUEL_KEYWORDS = {
        'DIESEL': ['diesel', 'hsd', 'high speed diesel', 'kraftstoff'],
        'PETROL': ['petrol', 'gasoline', 'benzin', 'unleaded'],
        'NATGAS': ['natural gas', 'erdgas', 'piped gas', 'cng', 'compressed natural gas', 'komprimiert'],
        'LPG': ['lpg', 'propane', 'flüssiggas', 'fluessiggas', 'liquefied petroleum'],
        'FUEL_OIL': ['fuel oil', 'furnace oil', 'heizöl', 'heizoil', 'heavy oil', 'leicht'],
        'COAL': ['coal', 'kohle', 'bituminous', 'anthracite', 'braunkohle'],
        'KEROSENE': ['kerosene', 'paraffin', 'atf', 'aviation turbine fuel', 'jet fuel'],
    }

    # Expected units per fuel type (for inconsistency detection)
    EXPECTED_UNITS = {
        'DIESEL': ['L', 'GAL'],
        'PETROL': ['L', 'GAL'],
        'NATGAS': ['M3'],  # KWH flagged as inconsistent (converted energy, not volume)
        'LPG': ['KG', 'L'],
        'FUEL_OIL': ['L', 'KG'],
        'COAL': ['KG'],
        'KEROSENE': ['L', 'GAL'],
    }

    def validate_headers(self, headers: List[str]) -> bool:
        """
        Validate CSV headers (supports English or German).

        Args:
            headers: List of column names

        Returns:
            True if valid

        Raises:
            ValueError: If required headers missing
        """
        # Normalize headers (German → English)
        normalized = [self.GERMAN_HEADERS.get(h, h) for h in headers]

        # Check required headers present
        missing = set(self.REQUIRED_HEADERS) - set(normalized)
        if missing:
            raise ValueError(
                f"Missing required headers: {', '.join(missing)}. "
                f"Found: {', '.join(headers)}"
            )

        return True

    def parse_row(self, row_dict: Dict[str, str], row_number: int) -> ParseResult:
        """
        Parse SAP MB51 row into Activity + SAPDetail.

        Steps:
        1. Check for duplicate row
        2. Normalize headers (German → English)
        3. Check BWART - ONLY 101 allowed
        4. Parse date
        5. Classify material (MATKL → keyword → unit → unclassified)
        6. Convert units
        7. Lookup facility
        8. Detect suspicious patterns
        9. Build Activity + SAPDetail data
        """
        result = ParseResult()

        try:
            # Step 1: Check for duplicates (hash entire row)
            row_hash = self._compute_row_hash(row_dict)
            if row_hash in self.seen_rows:
                result.add_flag('duplicate_row')
            else:
                self.seen_rows.add(row_hash)

            # Step 2: Normalize headers
            normalized_row = self._normalize_headers(row_dict)

            # Step 3: Check BWART - ONLY 101 (goods receipts) allowed
            bwart = normalized_row.get('BWART', '').strip()
            if bwart != '101':
                result.mark_excluded(f'BWART={bwart} excluded (only 101 goods receipts ingested)')
                return result

            # Step 4: Parse date
            try:
                posting_date = self._parse_date(normalized_row['BUDAT'])
            except ValueError as e:
                result.mark_failed(f"Invalid date format: {e}")
                return result

            # Step 5: Extract basic fields
            plant_code = normalized_row['WERKS'].strip()
            material_number = normalized_row['MATNR'].strip()
            material_desc = normalized_row['MAKTX'].strip()
            matkl = normalized_row.get('MATKL', '').strip() or None
            quantity_raw = self._parse_decimal(normalized_row['MENGE'])
            unit_raw = normalized_row['MEINS'].strip().upper()

            # Step 6: Classify material (waterfall)
            category, scope, classification_method = self._classify_material(
                matkl, material_desc, unit_raw
            )

            # Step 7: Convert units
            quantity_normalized, unit_normalized, conversion_factor, conversion_note = self._convert_unit(
                quantity_raw, unit_raw
            )

            # Step 8: Lookup facility
            facility = self._lookup_facility(plant_code)

            # Step 9: Detect suspicious patterns
            self._check_suspicious(
                result,
                plant_code,
                facility,
                matkl,
                classification_method,
                quantity_raw,
                category,
                unit_normalized
            )

            # Step 10: Build Activity data
            result.activity_data = {
                'facility': facility,
                'scope': scope,
                'category': category,
                'period_start': posting_date,
                'period_end': posting_date,
                'status': 'PENDING',
            }

            # Step 11: Build SAPDetail data
            result.detail_data = {
                'plant_code': plant_code,
                'material_number': material_number,
                'material_desc': material_desc,
                'material_group': matkl,
                'quantity_raw': quantity_raw,
                'unit_raw': unit_raw,
                'quantity_normalized': quantity_normalized,
                'unit_normalized': unit_normalized,
                'conversion_factor': conversion_factor,
                'conversion_note': conversion_note,
                'movement_type': bwart,
                'vendor_number': normalized_row.get('LIFNR', '').strip() or None,
                'po_number': normalized_row.get('EBELN', '').strip() or None,
                'classification_method': classification_method,
            }

        except Exception as e:
            result.mark_failed(f"Parse error: {str(e)}")

        return result

    def get_detail_model(self):
        """Return SAPDetail model class."""
        return SAPDetail

    # ===== Helper Methods =====

    def _compute_row_hash(self, row_dict: Dict[str, str]) -> str:
        """
        Compute hash of row for duplicate detection.

        Args:
            row_dict: CSV row dictionary

        Returns:
            MD5 hash of sorted key-value pairs
        """
        # Sort keys for consistent hashing
        sorted_items = sorted(row_dict.items())
        row_str = '|'.join(f"{k}={v}" for k, v in sorted_items)
        import hashlib
        return hashlib.md5(row_str.encode('utf-8')).hexdigest()

    def _normalize_headers(self, row_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Normalize German headers to English.

        Args:
            row_dict: Original CSV row

        Returns:
            Dict with English header names
        """
        normalized = {}
        for key, value in row_dict.items():
            english_key = self.GERMAN_HEADERS.get(key, key)
            normalized[english_key] = value
        return normalized

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse SAP date (YYYYMMDD or DD.MM.YYYY).

        Args:
            date_str: Date string

        Returns:
            datetime.date object

        Raises:
            ValueError: If date format invalid
        """
        date_str = date_str.strip()

        # Try YYYYMMDD format (English CSV)
        if len(date_str) == 8 and date_str.isdigit():
            return datetime.strptime(date_str, '%Y%m%d').date()

        # Try DD.MM.YYYY format (German CSV)
        if '.' in date_str:
            return datetime.strptime(date_str, '%d.%m.%Y').date()

        # Try other common formats
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Cannot parse date: {date_str}")

    def _parse_decimal(self, value_str: str) -> Decimal:
        """
        Parse decimal value, handling German/English formats.

        German format: 1.234,56 (dot=thousand, comma=decimal)
        English format: 1,234.56 (comma=thousand, dot=decimal)

        Args:
            value_str: Numeric string

        Returns:
            Decimal value

        Raises:
            ValueError: If not a valid number
        """
        value_str = value_str.strip()

        # Detect format by checking last separator
        if ',' in value_str and '.' in value_str:
            # Both separators present - check which comes last
            last_comma = value_str.rfind(',')
            last_dot = value_str.rfind('.')

            if last_comma > last_dot:
                # German format: 1.234,56
                value_str = value_str.replace('.', '').replace(',', '.')
            else:
                # English format: 1,234.56
                value_str = value_str.replace(',', '')

        elif ',' in value_str:
            # Only comma - could be German decimal or English thousand
            # Heuristic: if comma is in last 3 positions, it's German decimal
            comma_pos = value_str.rfind(',')
            if len(value_str) - comma_pos <= 3:
                # German decimal: 1234,56
                value_str = value_str.replace(',', '.')
            else:
                # English thousand: 12,345
                value_str = value_str.replace(',', '')

        elif '.' in value_str:
            # Only dot - could be English decimal or German thousand
            # Heuristic: if dot is in last 3 positions, it's English decimal
            dot_pos = value_str.rfind('.')
            if len(value_str) - dot_pos <= 3:
                # English decimal: 1234.56 (no change)
                pass
            else:
                # German thousand: 12.345
                value_str = value_str.replace('.', '')

        # Remove spaces
        value_str = value_str.replace(' ', '')

        try:
            return Decimal(value_str)
        except:
            raise ValueError(f"Invalid numeric value: {value_str}")

    def _classify_material(self, matkl: Optional[str], desc: str, unit: str) -> Tuple[str, int, str]:
        """
        Classify material using waterfall approach.

        Waterfall:
        1. MATKL → ClientMaterialGroupMapping (PRIMARY)
        2. Keyword match in description
        3. Unit-based inference
        4. UNCLASSIFIED

        Args:
            matkl: Material group code (nullable)
            desc: Material description
            unit: Unit of measure

        Returns:
            Tuple of (category, scope, classification_method)
        """
        # Step 1: Try MATKL mapping (PRIMARY)
        if matkl:
            mapping = ClientMaterialGroupMapping.objects.filter(
                org=self.org,
                matkl_code=matkl
            ).first()

            if mapping:
                return (mapping.fuel_type, mapping.scope, 'MATKL')

        # Step 2: Keyword matching in description
        desc_lower = desc.lower()
        for fuel_type, keywords in self.FUEL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    scope = 2 if fuel_type == 'ELECTRICITY' else 1
                    return (fuel_type, scope, 'KEYWORD')

        # Step 3: Unit-based inference
        if unit in ['L', 'GAL', 'LTR']:
            return ('UNCLASSIFIED', 1, 'UNCLASSIFIED')  # Likely fuel, but unknown type
        elif unit in ['M3']:
            return ('NATGAS', 1, 'MEINS')  # M3 usually natural gas
        elif unit in ['KWH', 'MWH']:
            return ('ELECTRICITY', 2, 'MEINS')

        # Step 4: Unclassified
        return ('UNCLASSIFIED', 1, 'UNCLASSIFIED')

    def _convert_unit(self, quantity: Decimal, unit: str) -> Tuple[Decimal, str, Optional[Decimal], Optional[str]]:
        """
        Convert unit to canonical form.

        Args:
            quantity: Quantity value
            unit: Original unit

        Returns:
            Tuple of (quantity_normalized, unit_normalized, conversion_factor, conversion_note)
        """
        unit_upper = unit.upper()

        # Check if conversion needed
        if unit_upper in self.UNIT_CONVERSIONS:
            target_unit, factor, note = self.UNIT_CONVERSIONS[unit_upper]
            return (quantity * factor, target_unit, factor, note)

        # No conversion needed
        return (quantity, unit_upper, None, None)

    def _lookup_facility(self, plant_code: str) -> Optional[object]:
        """
        Lookup facility by plant code.

        Args:
            plant_code: SAP plant code (WERKS)

        Returns:
            Facility instance or None if not found
        """
        lookup = PlantLookup.objects.filter(
            org=self.org,
            source_type='SAP',
            code=plant_code
        ).select_related('facility').first()

        return lookup.facility if lookup else None

    def _check_suspicious(
        self,
        result: ParseResult,
        plant_code: str,
        facility: Optional[object],
        matkl: Optional[str],
        classification_method: str,
        quantity: Decimal,
        category: str,
        unit_normalized: str
    ):
        """
        Apply suspicious detection rules.

        Rules:
        1. unknown_plant - plant code not in PlantLookup
        2. unknown_material - has MATKL but not mapped, OR no MATKL and unclassified
        3. negative_quantity - negative qty
        4. unit_inconsistency - wrong unit for fuel type

        Args:
            result: ParseResult to add flags to
            ... various fields to check
        """
        # Rule 1: Unknown plant
        if not facility:
            result.add_flag('unknown_plant')

        # Rule 2: Unknown material
        # Case A: Has MATKL but wasn't found in ClientMaterialGroupMapping
        if matkl and classification_method != 'MATKL':
            result.add_flag('unknown_material')
        # Case B: No MATKL and couldn't classify via keyword/unit
        elif not matkl and classification_method == 'UNCLASSIFIED':
            result.add_flag('unknown_material')

        # Rule 3: Negative quantity
        if quantity < 0:
            result.add_flag('negative_quantity')

        # Rule 4: Unit inconsistency
        if category in self.EXPECTED_UNITS:
            expected = self.EXPECTED_UNITS[category]
            if unit_normalized not in expected:
                result.add_flag('unit_inconsistency')
