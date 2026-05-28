"""
Travel expense parser (Concur/Navan formats).

Handles:
- Cabin class normalization (Y/J/C/F codes → ECONOMY/BUSINESS/etc.)
- IATA airport code validation
- Distance calculation via haversine formula for flights
- Trip grouping (trip_id for multi-leg journeys)
- Mode categorization (AIR, HOTEL, CAR)
- Currency conversion (reference only - not implemented yet)
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2
from .base import BaseParser, ParseResult
from apps.activities.models import TravelDetail


class TravelParser(BaseParser):
    """Parser for travel expense reports (Concur/Navan formats)."""

    # IATA airport coordinates database
    # Format: {code: (latitude, longitude, city_name)}
    # Covers ~100 major airports for Indian corporate travel
    IATA_COORDS = {
        # India - Major metros (Tier 1)
        'DEL': (28.5562, 77.1000, 'Delhi'),
        'BOM': (19.0896, 72.8656, 'Mumbai'),
        'BLR': (12.9499, 77.6677, 'Bangalore'),
        'HYD': (17.2403, 78.4294, 'Hyderabad'),
        'MAA': (12.9941, 80.1709, 'Chennai'),
        'CCU': (22.6547, 88.4467, 'Kolkata'),

        # India - Tier 2 cities
        'AMD': (23.0772, 72.6347, 'Ahmedabad'),
        'PNQ': (18.5793, 73.9197, 'Pune'),
        'COK': (10.1520, 76.4019, 'Kochi'),
        'TRV': (8.4821, 76.9200, 'Trivandrum'),
        'GOI': (15.3808, 73.8314, 'Goa'),
        'JAI': (26.8242, 75.8122, 'Jaipur'),
        'LKO': (26.7606, 80.8893, 'Lucknow'),
        'IXC': (30.6735, 76.7884, 'Chandigarh'),
        'NAG': (21.0922, 79.0472, 'Nagpur'),
        'BBI': (20.2444, 85.8178, 'Bhubaneswar'),
        'GAU': (26.1061, 91.5859, 'Guwahati'),
        'VNS': (25.4524, 82.8597, 'Varanasi'),
        'IXB': (26.6812, 88.3286, 'Bagdogra'),
        'RPR': (21.1804, 81.7388, 'Raipur'),
        'VGA': (16.5304, 80.7968, 'Vijayawada'),
        'IXR': (23.3142, 85.3217, 'Ranchi'),
        'SXR': (33.9871, 74.7742, 'Srinagar'),
        'IXJ': (32.6897, 74.8374, 'Jammu'),
        'IDR': (22.7216, 75.8011, 'Indore'),
        'UDR': (24.6177, 73.8961, 'Udaipur'),
        'IXZ': (11.6412, 92.7296, 'Port Blair'),
        'ATQ': (31.7096, 74.7973, 'Amritsar'),
        'IXU': (19.8629, 75.3981, 'Aurangabad'),
        'BDQ': (22.3362, 73.2263, 'Vadodara'),
        'STV': (21.1142, 72.7419, 'Surat'),

        # Southeast Asia
        'SIN': (1.3644, 103.9915, 'Singapore'),
        'BKK': (13.6900, 100.7501, 'Bangkok'),
        'DMK': (13.9126, 100.6067, 'Bangkok Don Mueang'),
        'KUL': (2.7456, 101.7072, 'Kuala Lumpur'),
        'CGK': (-6.1256, 106.6559, 'Jakarta'),
        'MNL': (14.5086, 121.0194, 'Manila'),
        'HAN': (21.2212, 105.8072, 'Hanoi'),
        'SGN': (10.8188, 106.6519, 'Ho Chi Minh City'),
        'PNH': (11.5466, 104.8442, 'Phnom Penh'),
        'RGN': (16.9073, 96.1332, 'Yangon'),
        'CMB': (7.1808, 79.8842, 'Colombo'),
        'KTM': (27.6966, 85.3591, 'Kathmandu'),

        # East Asia
        'HKG': (22.3080, 113.9185, 'Hong Kong'),
        'PVG': (31.1434, 121.8052, 'Shanghai Pudong'),
        'PEK': (40.0799, 116.6031, 'Beijing'),
        'CAN': (23.3924, 113.2988, 'Guangzhou'),
        'NRT': (35.7647, 140.3864, 'Tokyo Narita'),
        'HND': (35.5494, 139.7798, 'Tokyo Haneda'),
        'ICN': (37.4602, 126.4407, 'Seoul Incheon'),
        'TPE': (25.0797, 121.2342, 'Taipei'),

        # Middle East
        'DXB': (25.2532, 55.3657, 'Dubai'),
        'AUH': (24.4330, 54.6511, 'Abu Dhabi'),
        'DOH': (25.2731, 51.6080, 'Doha'),
        'BAH': (26.2708, 50.6336, 'Bahrain'),
        'MCT': (23.5933, 58.2844, 'Muscat'),
        'KWI': (29.2267, 47.9689, 'Kuwait'),
        'RUH': (24.9578, 46.6988, 'Riyadh'),
        'JED': (21.6796, 39.1567, 'Jeddah'),
        'IST': (41.2753, 28.7519, 'Istanbul'),

        # Europe
        'LHR': (51.4700, -0.4543, 'London Heathrow'),
        'LGW': (51.1481, -0.1903, 'London Gatwick'),
        'MAN': (53.3537, -2.2750, 'Manchester'),
        'EDI': (55.9500, -3.3636, 'Edinburgh'),
        'CDG': (49.0097, 2.5479, 'Paris'),
        'FRA': (50.0379, 8.5622, 'Frankfurt'),
        'MUC': (48.3537, 11.7750, 'Munich'),
        'AMS': (52.3105, 4.7683, 'Amsterdam'),
        'ZRH': (47.4582, 8.5556, 'Zurich'),
        'VIE': (48.1103, 16.5697, 'Vienna'),
        'FCO': (41.8003, 12.2389, 'Rome'),
        'MAD': (40.4839, -3.5680, 'Madrid'),
        'BCN': (41.2974, 2.0833, 'Barcelona'),
        'CPH': (55.6180, 12.6508, 'Copenhagen'),
        'ARN': (59.6519, 17.9186, 'Stockholm'),
        'OSL': (60.1939, 11.1004, 'Oslo'),
        'BRU': (50.9010, 4.4856, 'Brussels'),

        # North America
        'JFK': (40.6413, -73.7781, 'New York JFK'),
        'EWR': (40.6895, -74.1745, 'Newark'),
        'LAX': (33.9416, -118.4085, 'Los Angeles'),
        'SFO': (37.6213, -122.3790, 'San Francisco'),
        'ORD': (41.9742, -87.9073, 'Chicago'),
        'IAD': (38.9531, -77.4565, 'Washington Dulles'),
        'DFW': (32.8998, -97.0403, 'Dallas'),
        'ATL': (33.6407, -84.4277, 'Atlanta'),
        'SEA': (47.4502, -122.3088, 'Seattle'),
        'BOS': (42.3656, -71.0096, 'Boston'),
        'YYZ': (43.6777, -79.6248, 'Toronto'),
        'YVR': (49.1939, -123.1844, 'Vancouver'),

        # Australia & Pacific
        'SYD': (-33.9399, 151.1753, 'Sydney'),
        'MEL': (-37.6690, 144.8410, 'Melbourne'),
        'BNE': (-27.3942, 153.1218, 'Brisbane'),
        'PER': (-31.9403, 115.9671, 'Perth'),
        'AKL': (-37.0082, 174.7850, 'Auckland'),

        # Africa
        'JNB': (-26.1392, 28.2460, 'Johannesburg'),
        'CPT': (-33.9715, 18.6021, 'Cape Town'),
        'NBO': (-1.3192, 36.9278, 'Nairobi'),
        'CAI': (30.1219, 31.4056, 'Cairo'),
        'ADD': (8.9779, 38.7992, 'Addis Ababa'),

        # South America
        'GRU': (-23.4356, -46.4731, 'Sao Paulo'),
        'GIG': (-22.8099, -43.2505, 'Rio de Janeiro'),
        'BOG': (4.7016, -74.1469, 'Bogota'),
        'LIM': (-12.0219, -77.1143, 'Lima'),
    }

    # Mode normalization (Navan uses FLIGHT, model expects AIR)
    MODE_ALIASES = {
        'FLIGHT': 'AIR',
        'AIR': 'AIR',
        'HOTEL': 'HOTEL',
        'CAR': 'CAR',
        'RAIL': 'RAIL',
    }

    # Cabin class normalization
    CABIN_CLASS_MAP = {
        'Y': 'ECONOMY',
        'W': 'PREMIUM',
        'J': 'BUSINESS',
        'C': 'BUSINESS',
        'F': 'FIRST',
        'BUS': 'BUSINESS',
        'PREM': 'PREMIUM',
        'PE': 'PREMIUM',
        'ECO': 'ECONOMY',
        'ECON': 'ECONOMY',
        'ECONOMY': 'ECONOMY',
        'PREMIUM': 'PREMIUM',
        'BUSINESS': 'BUSINESS',
        'FIRST': 'FIRST',
    }

    # Mode to Activity.category mapping
    MODE_CATEGORY_MAP = {
        'AIR': 'FLIGHT',
        'HOTEL': 'HOTEL',
        'CAR': 'CAR',
        'RAIL': 'UNCLASSIFIED',  # Not in Activity.CATEGORY_CHOICES yet
    }

    # Header aliases
    HEADER_ALIASES = {
        'travel_date': 'expense_date',
        'transaction_date': 'expense_date',
        'date': 'expense_date',
        'report_id': 'trip_id',
        'booking_id': 'trip_id',
        'emp_id': 'employee_id',
        'employee': 'employee_id',
        'dept': 'department',
        'transport_mode': 'mode',
        'type': 'mode',
        'from': 'origin',
        'departure': 'origin',
        'to': 'destination',
        'arrival': 'destination',
        'class': 'cabin_class',
        'travel_class': 'cabin_class',
        'num_nights': 'nights',
        'hotel_nights': 'nights',
        'amount': 'amount_raw',
        'cost': 'amount_raw',  # Navan uses 'cost'
        'total': 'amount_raw',
        'spend': 'amount_raw',
        'curr': 'currency',
        'carbon_kg': 'carbon_kg_navan',  # Navan provides this, we ignore it
    }

    REQUIRED_HEADERS = ['trip_id', 'employee_id', 'expense_date', 'mode', 'amount_raw', 'currency']
    OPTIONAL_HEADERS = ['department', 'cost_center', 'origin', 'destination', 'cabin_class', 'nights', 'carbon_kg_navan']

    def validate_headers(self, headers: List[str]) -> bool:
        """
        Validate travel CSV headers (with alias support).

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
        Parse travel expense row into Activity + TravelDetail.

        Steps:
        1. Extract and validate fields
        2. Parse date
        3. Normalize mode (AIR/HOTEL/CAR)
        4. Normalize cabin class if AIR mode
        5. Validate IATA codes if AIR mode
        6. Calculate distance if AIR mode
        7. Parse amount (with thousands separator handling)
        8. Build Activity + TravelDetail data
        """
        result = ParseResult()

        try:
            # Step 1: Normalize headers and extract fields
            normalized_row = self._normalize_headers(row_dict)
            trip_id = normalized_row['trip_id'].strip()
            employee_id = normalized_row['employee_id'].strip()
            expense_date_str = normalized_row['expense_date'].strip()
            mode_raw = normalized_row['mode'].strip().upper()
            amount_str = normalized_row['amount_raw'].strip()
            currency = normalized_row['currency'].strip().upper()

            # Optional fields
            department = normalized_row.get('department', '').strip() or None
            cost_center = normalized_row.get('cost_center', '').strip() or None
            origin_raw = (normalized_row.get('origin') or '').strip().upper()
            destination_raw = (normalized_row.get('destination') or '').strip().upper()
            cabin_class_raw = (normalized_row.get('cabin_class') or '').strip().upper()
            nights_str = (normalized_row.get('nights') or '').strip()

            # Step 2: Parse date
            try:
                expense_date = self._parse_date(expense_date_str)
            except ValueError as e:
                result.mark_failed(f"Invalid date format: {e}")
                return result

            # Step 3: Normalize mode (Navan uses FLIGHT, model expects AIR)
            mode_normalized = self.MODE_ALIASES.get(mode_raw)
            if not mode_normalized:
                result.mark_failed(f"Invalid mode: {mode_raw} (expected AIR, FLIGHT, HOTEL, CAR, or RAIL)")
                return result

            # Step 4: Parse amount (with thousands separator handling)
            # Handle malformed CSV: if amount is empty/zero and currency contains digits, swap them
            if (not amount_str or amount_str == '0') and currency.replace(',', '').replace('.', '').isdigit():
                # Column shift detected - swap amount and currency
                amount_str, currency = currency, 'INR'  # Assume INR if shifted

            try:
                amount_raw = self._parse_decimal(amount_str)
            except ValueError as e:
                result.mark_failed(f"Invalid amount: {e}")
                return result

            # Step 4a: Check for negative amount
            if amount_raw < 0:
                result.add_flag('negative_amount')

            # Step 4b: Convert non-INR currency to INR with full traceability
            amount_inr = amount_raw
            fx_rate_used = None
            fx_rate_date = None
            fx_source = None
            fx_note = None

            if currency == 'INR':
                # No conversion needed
                fx_rate_used = Decimal('1.000000')
                fx_source = 'NATIVE_INR'
            else:
                # Try to convert using CurrencyConversionRate table
                from apps.core.models import CurrencyConversionRate
                try:
                    conversion_rate = CurrencyConversionRate.objects.filter(
                        currency_code=currency
                    ).order_by('-effective_date').first()

                    if conversion_rate:
                        fx_rate_used = conversion_rate.rate_to_inr
                        fx_rate_date = conversion_rate.effective_date
                        fx_source = f"CurrencyConversionRate:{conversion_rate.effective_date}"
                        amount_inr = (amount_raw * fx_rate_used).quantize(Decimal('0.01'))
                        fx_note = f"Used latest available rate for {currency}"
                    else:
                        # No conversion rate found - flag for review
                        result.add_flag('fx_rate_missing')
                        amount_inr = None
                        fx_note = f"No FX rate found for {currency}"
                except Exception as e:
                    result.add_flag('conversion_error')
                    amount_inr = None
                    fx_note = f"FX conversion error: {str(e)}"

            # Step 5: Handle mode-specific logic
            origin = None
            destination = None
            distance_km = None
            cabin_class = None
            cabin_class_normalized = None
            nights = None
            distance_method = None

            if mode_normalized == 'AIR':
                # Validate IATA codes
                if not origin_raw or not destination_raw:
                    result.add_flag('missing_airport')
                else:
                    origin = origin_raw
                    destination = destination_raw

                    # Check if codes exist in our database
                    if origin not in self.IATA_COORDS:
                        result.add_flag('unknown_airport')
                    if destination not in self.IATA_COORDS:
                        result.add_flag('unknown_airport')

                    # Calculate distance if both codes valid
                    if origin in self.IATA_COORDS and destination in self.IATA_COORDS:
                        distance_km = self._haversine_distance(origin, destination)
                        distance_method = 'GREAT_CIRCLE'

                # Normalize cabin class
                if cabin_class_raw:
                    cabin_class = cabin_class_raw
                    cabin_class_normalized = self.CABIN_CLASS_MAP.get(cabin_class_raw)
                    if not cabin_class_normalized:
                        # Unknown cabin class code
                        result.add_flag('unknown_cabin_class')
                        cabin_class_normalized = None

            elif mode_normalized == 'HOTEL':
                # Parse nights
                if nights_str:
                    try:
                        nights = int(nights_str)
                        if nights < 0:
                            # Negative nights is structurally invalid - fail the row
                            result.mark_failed(f"Invalid nights value: {nights} (cannot be negative)")
                            return result
                    except ValueError:
                        result.mark_failed(f"Invalid nights value: {nights_str}")
                        return result
                else:
                    # Hotel without nights - flag for review
                    result.add_flag('missing_nights')

            elif mode_normalized == 'CAR':
                # CAR uses spend-based method (no distance calculation)
                distance_method = 'SPEND_BASED'

            # Step 6: Map mode to Activity category
            category = self.MODE_CATEGORY_MAP.get(mode_normalized, 'UNCLASSIFIED')

            # Step 7: Build Activity data
            # NOTE: emissions_kgco2e field left NULL - calculated later
            result.activity_data = {
                'facility': None,  # Travel expenses not tied to facility
                'scope': 3,  # All travel is Scope 3
                'category': category,
                'period_start': expense_date,
                'period_end': expense_date,
                'is_cross_month': False,  # Single-date expense
                'status': 'PENDING',
                # emissions_kgco2e: NULL - to be calculated later
            }

            # Step 8: Build TravelDetail data
            result.detail_data = {
                'trip_id': trip_id,
                'employee_id': employee_id,
                'department': department,
                'cost_center': cost_center,
                'mode': mode_normalized,  # Store normalized mode (AIR not FLIGHT)
                'origin': origin,  # May contain invalid IATA code if flagged
                'destination': destination,  # May contain invalid IATA code if flagged
                'distance_km': distance_km,
                'cabin_class': cabin_class_normalized,
                'cabin_class_raw': cabin_class if cabin_class_raw else None,
                'nights': nights,
                'amount_raw': amount_raw,
                'currency': currency,
                'amount_inr': amount_inr,
                # FX traceability
                'fx_rate_used': fx_rate_used,
                'fx_rate_date': fx_rate_date,
                'fx_source': fx_source,
                'fx_note': fx_note,
                'distance_method': distance_method,
            }

        except Exception as e:
            result.mark_failed(f"Parse error: {str(e)}")

        return result

    def get_detail_model(self):
        """Return TravelDetail model class."""
        return TravelDetail

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
            # Skip None key (happens when CSV has more fields than headers)
            if key is None:
                continue
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

    def _haversine_distance(self, origin_code: str, dest_code: str) -> Decimal:
        """
        Calculate great circle distance between two airports using haversine formula.

        Formula:
        a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c

        Where R = Earth radius = 6371 km

        Args:
            origin_code: IATA airport code
            dest_code: IATA airport code

        Returns:
            Distance in km (Decimal with 2 decimal places)
        """
        lat1, lon1, _ = self.IATA_COORDS[origin_code]
        lat2, lon2, _ = self.IATA_COORDS[dest_code]

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Earth radius in km
        R = 6371

        distance = R * c

        return Decimal(str(round(distance, 2)))
