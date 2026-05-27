"""
Base parser interface for all source types.

Parsers handle source-specific logic (field mapping, validation, classification).
IngestionService handles orchestration (transactions, audit, RawRecords).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ParseResult:
    """
    Data contract between parser and ingestion service.

    Parsers return this object for each CSV row.
    Service uses it to create Activity + Detail records.
    """
    # Fields for Activity model
    activity_data: Dict[str, Any] = field(default_factory=dict)

    # Fields for detail model (SAPDetail/UtilityDetail/TravelDetail)
    detail_data: Dict[str, Any] = field(default_factory=dict)

    # Parse status
    parse_status: str = 'SUCCESS'  # SUCCESS/FAILED/EXCLUDED
    parse_error: Optional[str] = None
    exclude_reason: Optional[str] = None

    # Suspicious flags detected by parser
    suspicious_flags: List[str] = field(default_factory=list)

    def mark_failed(self, error: str):
        """Mark this parse as failed."""
        self.parse_status = 'FAILED'
        self.parse_error = error

    def mark_excluded(self, reason: str):
        """Mark this row as excluded (e.g., BWART=122 returns)."""
        self.parse_status = 'EXCLUDED'
        self.exclude_reason = reason

    def add_flag(self, flag_name: str):
        """Add a suspicious flag."""
        if flag_name not in self.suspicious_flags:
            self.suspicious_flags.append(flag_name)


class BaseParser(ABC):
    """
    Abstract base parser for all source types.

    Each source type (SAP, Utility, Travel) implements:
    - parse_row(): Convert CSV row to Activity + Detail data
    - get_detail_model(): Return the detail model class
    """

    def __init__(self, org):
        """
        Initialize parser for an organization.

        Args:
            org: Organization instance (for lookups like PlantLookup, MaterialMapping)
        """
        self.org = org

    @abstractmethod
    def parse_row(self, row_dict: Dict[str, str], row_number: int) -> ParseResult:
        """
        Parse one CSV row into Activity + Detail data.

        Args:
            row_dict: Dictionary of CSV row (column headers as keys)
            row_number: 1-indexed row number from CSV

        Returns:
            ParseResult containing activity_data, detail_data, and flags

        Raises:
            Should NOT raise exceptions - catch and return ParseResult with parse_status='FAILED'
        """
        pass

    @abstractmethod
    def get_detail_model(self):
        """
        Return the detail model class for this parser.

        Returns:
            SAPDetail, UtilityDetail, or TravelDetail class
        """
        pass

    @abstractmethod
    def validate_headers(self, headers: List[str]) -> bool:
        """
        Validate that CSV has required headers.

        Args:
            headers: List of column names from CSV

        Returns:
            True if headers are valid, False otherwise

        Raises:
            ValueError with descriptive message if headers invalid
        """
        pass
