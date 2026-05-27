"""
Travel expense report parser (Concur/Navan format).

Handles:
- Cabin class normalization (Y→ECONOMY, J→BUSINESS)
- IATA code validation
- Distance calculation (haversine for flights)
- Trip grouping (multi-leg trips)
- Navan carbon_kg column (ignored)
"""
from typing import List, Dict
from .base import BaseParser, ParseResult
from apps.activities.models import TravelDetail


class TravelParser(BaseParser):
    """Parser for travel expense reports (Concur/Navan)."""

    REQUIRED_HEADERS = ['trip_id', 'employee_id', 'travel_date', 'mode', 'amount', 'currency']

    def validate_headers(self, headers: List[str]) -> bool:
        """Validate travel CSV headers."""
        missing = set(self.REQUIRED_HEADERS) - set(headers)
        if missing:
            raise ValueError(f"Missing required headers: {', '.join(missing)}")
        return True

    def parse_row(self, row_dict: Dict[str, str], row_number: int) -> ParseResult:
        """Parse travel row. TODO: Implement."""
        result = ParseResult()
        result.mark_failed("Travel parser not yet implemented")
        return result

    def get_detail_model(self):
        """Return TravelDetail model class."""
        return TravelDetail
