"""
Utility bill parser (TSSPDCL format).

Handles:
- Gap detection (timeline per service_number - checks if gap > 35 days)
- Unit ambiguity (kVAh vs kWh - apparent power vs active power)
- Unknown meter flagging
- Cross-month period detection (informational)
- CEA 2024 India grid emission factor application
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict
from .base import BaseParser, ParseResult
from apps.activities.models import UtilityDetail
from apps.core.models import PlantLookup, EmissionFactor


class UtilityParser(BaseParser):
    """Parser for utility bills (TSSPDCL format - Telangana DISCOM)."""

    def __init__(self, org):
        """Initialize parser with org and timeline tracking for gap detection."""
        super().__init__(org)
        # Track timeline per service_number for gap detection
        # Format: {service_no: [(period_start, period_end, row_number), ...]}
        self.service_timelines: Dict[str, List[Tuple[date, date, int]]] = defaultdict(list)

    # Header aliases (common variations in utility exports)
    HEADER_ALIASES = {
        'service_number': 'service_no',
        'meter_no': 'service_no',
        'meter_number': 'service_no',
        'from_date': 'period_start',
        'start_date': 'period_start',
        'to_date': 'period_end',
        'end_date': 'period_end',
        'consumption': 'units_kwh',
        'units': 'units_kwh',
        'kwh': 'units_kwh',
        'bill_amount': 'amount_inr',
        'amount': 'amount_inr',
        'tariff_category': 'tariff',
        # Unit column (optional)
        'uom': 'unit',
        'unit_of_measure': 'unit',
    }

    REQUIRED_HEADERS = ['service_no', 'period_start', 'period_end', 'units_kwh', 'tariff', 'amount_inr']
    OPTIONAL_HEADERS = ['unit']  # Unit of measure column

    # Gap detection threshold (days)
    GAP_THRESHOLD_DAYS = 35  # Normal billing cycle is 28-32 days

    # CEA 2024 grid emission factor for India (kgCO2e per kWh)
    CEA_2024_FACTOR = Decimal('0.716')

    def validate_headers(self, headers: List[str]) -> bool:
        """
        Validate utility CSV headers (with alias support).

        Args:
            headers: List of column names

        Returns:
            True if valid

        Raises:
            ValueError: If required headers missing
        """
        # Normalize headers using aliases
        normalized = [self.HEADER_ALIASES.get(h.lower(), h) for h in headers]

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
        Parse utility bill row into Activity + UtilityDetail.

        Steps:
        1. Extract and validate fields
        2. Parse dates
        3. Detect cross-month period
        4. Lookup facility by service number
        5. Check for unit ambiguity (kVAh)
        6. Track timeline for gap detection
        7. Build Activity + UtilityDetail data
        """
        result = ParseResult()

        try:
            # Step 1: Normalize headers and extract fields
            normalized_row = self._normalize_headers(row_dict)
            service_no = normalized_row['service_no'].strip()
            period_start_str = normalized_row['period_start'].strip()
            period_end_str = normalized_row['period_end'].strip()
            units_str = normalized_row['units_kwh'].strip()
            tariff = normalized_row['tariff'].strip()
            amount_str = normalized_row['amount_inr'].strip()

            # Step 2: Parse dates
            try:
                period_start = self._parse_date(period_start_str)
                period_end = self._parse_date(period_end_str)
            except ValueError as e:
                result.mark_failed(f"Invalid date format: {e}")
                return result

            # Validate date range
            if period_end < period_start:
                result.mark_failed(f"Invalid date range: end ({period_end}) before start ({period_start})")
                return result

            # Step 3: Parse numeric values (with thousands separator handling)
            try:
                kwh_consumed = self._parse_decimal(units_str)
                amount_inr = self._parse_decimal(amount_str)
            except ValueError as e:
                result.mark_failed(f"Invalid numeric value: {e}")
                return result

            # Step 3a: Check for negative values
            if kwh_consumed < 0:
                result.add_flag('negative_consumption')

            if amount_inr < 0:
                result.add_flag('negative_amount')

            # Step 4: Detect unit type
            # Priority: 1) unit column, 2) infer from tariff/field name, 3) default kWh
            unit_raw = 'kWh'  # Default assumption

            # Check if CSV has explicit unit column
            if 'unit' in normalized_row and normalized_row['unit'].strip():
                unit_raw = normalized_row['unit'].strip()
            # Else infer from tariff or units field (legacy behavior)
            elif 'kvah' in tariff.lower() or 'kvah' in units_str.lower():
                unit_raw = 'kVAh'

            # Flag if unit is not kWh (ambiguous or needs conversion)
            if unit_raw.upper() not in ['KWH', 'KWHR']:
                result.add_flag('unit_ambiguous')

            # Step 5: Check for cross-month period
            is_cross_month = period_start.month != period_end.month or period_start.year != period_end.year

            # Step 6: Lookup facility by service number
            facility = self._lookup_facility(service_no)
            if not facility:
                result.add_flag('unknown_meter')

            # Step 7: Check for overlaps in this service's timeline
            self._check_overlap(result, service_no, period_start, period_end, row_number)

            # Step 8: Track timeline for gap detection (checked after all rows parsed)
            self.service_timelines[service_no].append((period_start, period_end, row_number))

            # NOTE: Gap detection happens in finalize_parsing() after all rows processed
            # This handles unsorted data correctly

            # Step 10: Get emission factor (for reference, not calculation)
            # NOTE: Emission calculation happens later in separate service layer
            emission_factor = self._get_emission_factor()

            # Step 11: Build Activity data
            # NOTE: emissions_kgco2e field left NULL - calculated later
            result.activity_data = {
                'facility': facility,
                'scope': 2,  # Electricity is always Scope 2
                'category': 'ELECTRICITY',
                'period_start': period_start,
                'period_end': period_end,
                'is_cross_month': is_cross_month,
                'status': 'PENDING',
                # emissions_kgco2e: NULL - to be calculated later
            }

            # Step 12: Build UtilityDetail data
            result.detail_data = {
                'service_number': service_no,
                'tariff_category': tariff,
                'kwh_consumed': kwh_consumed,
                'unit_raw': unit_raw,
                'billing_amount_inr': amount_inr,
                'grid_emission_factor': emission_factor,  # Reference only
                'emission_factor_source': 'CEA_2024',
            }

        except Exception as e:
            result.mark_failed(f"Parse error: {str(e)}")

        return result

    def get_detail_model(self):
        """Return UtilityDetail model class."""
        return UtilityDetail

    # ===== Helper Methods =====

    def _normalize_headers(self, row_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Normalize headers using aliases.

        Args:
            row_dict: Original CSV row

        Returns:
            Dict with normalized header names
        """
        normalized = {}
        for key, value in row_dict.items():
            normalized_key = self.HEADER_ALIASES.get(key.lower(), key)
            normalized[normalized_key] = value
        return normalized

    def _parse_decimal(self, value_str: str) -> Decimal:
        """
        Parse decimal value, handling thousands separators.

        Handles:
        - 1,234.56 (English: comma=thousand, dot=decimal)
        - 1234.56 (no thousand separator)
        - 1234 (integer)

        Args:
            value_str: Numeric string

        Returns:
            Decimal value

        Raises:
            ValueError: If not a valid number
        """
        value_str = value_str.strip()

        # Remove thousands separators (comma in English format)
        # Utility bills in India typically use English format
        value_str = value_str.replace(',', '').replace(' ', '')

        try:
            return Decimal(value_str)
        except:
            raise ValueError(f"Invalid numeric value: {value_str}")

    def _parse_date(self, date_str: str) -> date:
        """
        Parse date in YYYY-MM-DD format.

        Args:
            date_str: Date string

        Returns:
            date object

        Raises:
            ValueError: If date format invalid
        """
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # Try other common formats
            for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse date: {date_str}")

    def _lookup_facility(self, service_no: str) -> Optional[object]:
        """
        Lookup facility by service number (meter ID).

        Args:
            service_no: Utility meter/service number

        Returns:
            Facility instance or None if not found
        """
        lookup = PlantLookup.objects.filter(
            org=self.org,
            source_type='UTILITY',
            code=service_no
        ).select_related('facility').first()

        return lookup.facility if lookup else None

    def _get_emission_factor(self) -> Decimal:
        """
        Get CEA 2024 grid emission factor for India (reference only).

        NOTE: This is stored in UtilityDetail for reference/audit.
        Actual emissions calculation happens in separate service layer.

        Returns:
            Emission factor in kgCO2e per kWh
        """
        # Try to get from database
        ef = EmissionFactor.objects.filter(fuel_type='ELECTRICITY').first()
        if ef:
            return ef.factor_kgco2e

        # Fallback to hardcoded CEA 2024 value
        return self.CEA_2024_FACTOR

    def _check_overlap(
        self,
        result: ParseResult,
        service_no: str,
        current_start: date,
        current_end: date,
        row_number: int
    ):
        """
        Check for overlapping billing periods.

        An overlap is when current period overlaps with any previous period:
        - Current starts before previous ends
        - AND current ends after previous starts

        Args:
            result: ParseResult to add flags to
            service_no: Service number being checked
            current_start: Start date of current period
            current_end: End date of current period
            row_number: Current row number
        """
        previous_bills = self.service_timelines.get(service_no, [])

        for prev_start, prev_end, prev_row in previous_bills:
            # Check for overlap
            # Overlap exists if: current_start < prev_end AND current_end > prev_start
            if current_start < prev_end and current_end > prev_start:
                result.add_flag('overlap')
                break  # Only flag once

    def finalize_parsing(self) -> Dict[int, List[str]]:
        """
        Finalize parsing - check for gaps after all rows processed.

        This method is called by the ingestion service after all rows are parsed.
        It sorts the timeline per service and checks for gaps, handling unsorted data.

        Returns:
            Dict of {row_number: [flag_names]} to apply to activities
        """
        flags_to_apply = {}

        for service_no, bills_data in self.service_timelines.items():
            # Sort bills by period_start to handle unsorted data
            sorted_bills = sorted(bills_data, key=lambda x: x[0])

            # Check gaps between consecutive bills
            for i in range(1, len(sorted_bills)):
                prev_start, prev_end, prev_row = sorted_bills[i - 1]
                curr_start, curr_end, curr_row = sorted_bills[i]

                # Calculate gap from previous end to current start
                gap_days = (curr_start - prev_end).days

                # Flag if gap > threshold
                if gap_days > self.GAP_THRESHOLD_DAYS:
                    if curr_row not in flags_to_apply:
                        flags_to_apply[curr_row] = []
                    flags_to_apply[curr_row].append('gap')

        return flags_to_apply

