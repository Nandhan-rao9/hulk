from django.db import models
from apps.core.models import Organization, User, Facility
from apps.ingestion.models import SourceFile, RawRecord


class Activity(models.Model):
    """
    Thin canonical table for emissions activities.
    One activity per CSV row that passes parsing.
    Source-specific fields are in detail tables (SAPDetail, UtilityDetail, TravelDetail).
    """
    SCOPE_CHOICES = [
        (1, 'Scope 1'),
        (2, 'Scope 2'),
        (3, 'Scope 3'),
    ]

    CATEGORY_CHOICES = [
        ('DIESEL', 'Diesel'),
        ('PETROL', 'Petrol'),
        ('NATGAS', 'Natural Gas'),
        ('LPG', 'LPG'),
        ('FUEL_OIL', 'Fuel Oil'),
        ('COAL', 'Coal'),
        ('KEROSENE', 'Kerosene'),
        ('ELECTRICITY', 'Electricity'),
        ('FLIGHT', 'Flight'),
        ('HOTEL', 'Hotel'),
        ('CAR', 'Car'),
        ('UNCLASSIFIED', 'Unclassified'),
    ]

    STATUS_CHOICES = [
        ('FLAGGED', 'Flagged'),  # Has issues, needs review
        ('PENDING', 'Pending Admin Approval'),  # Analyst approved, waiting for admin
        ('APPROVED', 'Approved'),  # Admin approved (final)
        ('LOCKED', 'Locked'),  # Period locked
        ('INVALIDATED', 'Invalidated'),  # File/activity invalidated
    ]

    MANUAL_FLAG_REASONS = [
        ('incorrect_amount', 'Incorrect Amount'),
        ('incorrect_date', 'Incorrect Date'),
        ('incorrect_plant', 'Incorrect Plant Code'),
        ('duplicate_suspected', 'Suspected Duplicate'),
        ('missing_documentation', 'Missing Documentation'),
        ('unusual_quantity', 'Unusual Quantity'),
        ('emissions_calculation_failed', 'Emissions Calculation Failed'),
        ('other', 'Other'),
    ]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='activities')
    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name='activities')
    raw_record = models.OneToOneField(
        RawRecord,
        on_delete=models.CASCADE,
        related_name='activity',
        null=True,
        blank=True,
        help_text="Nullable for manual entries (future scope)"
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='activities',
        null=True,
        blank=True,
        help_text="Null if plant code not found during ingestion"
    )
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Nullable for single-date records like SAP"
    )
    period_end = models.DateField(help_text="Attribution date - month lock checks this field")
    emissions_kgco2e = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Calculated emissions in kgCO2e. NULL = not yet calculated. Calculation done post-ingestion via management command or background task."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='FLAGGED')
    is_suspicious = models.BooleanField(default=False)
    flag_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Pipe-delimited if multiple flags, e.g., 'unknown_plant|negative_quantity'"
    )
    is_cross_month = models.BooleanField(
        default=False,
        help_text="Informational only, not blocking"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='approved_activities',
        null=True,
        blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activities'
        verbose_name_plural = 'activities'
        ordering = ['-period_end', '-created_at']
        indexes = [
            models.Index(fields=['org', 'status']),
            models.Index(fields=['org', 'period_end']),
            models.Index(fields=['facility', 'period_end']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.period_end} ({self.get_status_display()})"

    def calculate_emissions(self):
        """
        Calculate emissions_kgco2e based on source type and emission factors.

        Returns:
            bool: True if successful (numeric value computed), False if failed (None result)
        """
        from apps.core.models import EmissionFactor
        from decimal import Decimal
        import logging

        logger = logging.getLogger(__name__)

        try:
            if hasattr(self, 'sap_detail'):
                self.emissions_kgco2e = self._calculate_sap_emissions()
            elif hasattr(self, 'utility_detail'):
                self.emissions_kgco2e = self._calculate_utility_emissions()
            elif hasattr(self, 'travel_detail'):
                self.emissions_kgco2e = self._calculate_travel_emissions()
            else:
                logger.warning(f"Activity {self.id} has no detail record, cannot calculate emissions")
                return False

            self.save(update_fields=['emissions_kgco2e'])

            # Return True only if we actually calculated a numeric value
            if self.emissions_kgco2e is not None:
                return True
            else:
                logger.warning(f"Activity {self.id}: Calculation returned None (factor missing or unit mismatch)")
                return False

        except EmissionFactor.DoesNotExist as e:
            logger.warning(f"Activity {self.id}: Missing emission factor - {e}")
            self.emissions_kgco2e = None
            return False
        except Exception as e:
            logger.error(f"Activity {self.id}: Emissions calculation failed - {e}")
            self.emissions_kgco2e = None
            return False

    def _calculate_sap_emissions(self):
        """Calculate emissions for SAP fuel/procurement data."""
        from apps.core.models import EmissionFactor
        from decimal import Decimal

        detail = self.sap_detail

        # Get emission factor for this fuel type
        try:
            factor = EmissionFactor.objects.get(fuel_type=self.category)
        except EmissionFactor.DoesNotExist:
            # Log and return None for unclassified/unknown fuels
            import logging
            logging.getLogger(__name__).warning(
                f"Activity {self.id}: No emission factor for category '{self.category}'"
            )
            return None

        # Check unit compatibility
        if factor.unit != detail.unit_normalized:
            # Flag unit mismatch instead of breaking
            import logging
            logging.getLogger(__name__).warning(
                f"Activity {self.id}: Unit mismatch - factor expects {factor.unit}, got {detail.unit_normalized}"
            )

            # Add flag if not already present
            flags = self.flag_reason.split('|') if self.flag_reason else []
            if 'unit_mismatch' not in flags:
                flags.append('unit_mismatch')
                self.flag_reason = '|'.join(flags)
                self.is_suspicious = True
                self.status = 'FLAGGED'
                self.save(update_fields=['flag_reason', 'is_suspicious', 'status'])
                self.source_file.sync_counters()

            return None

        # Calculate: quantity × emission factor
        emissions = detail.quantity_normalized * factor.factor_kgco2e
        return emissions

    def _calculate_utility_emissions(self):
        """Calculate emissions for utility electricity data."""
        from decimal import Decimal

        detail = self.utility_detail

        # Simple case - grid emission factor already stored in detail record
        emissions = detail.kwh_consumed * detail.grid_emission_factor
        return emissions

    def _calculate_travel_emissions(self):
        """Calculate emissions for travel data (flights, hotels, ground transport)."""
        from apps.core.models import EmissionFactor
        from decimal import Decimal
        import logging

        logger = logging.getLogger(__name__)
        detail = self.travel_detail

        # Flight: distance × cabin class factor
        if detail.mode == 'AIR' and detail.distance_km:
            cabin_map = {
                'ECONOMY': 'FLIGHT_ECONOMY',
                'PREMIUM': 'FLIGHT_PREMIUM',
                'BUSINESS': 'FLIGHT_BUSINESS',
                'FIRST': 'FLIGHT_FIRST',
            }

            fuel_type = cabin_map.get(detail.cabin_class, 'FLIGHT_ECONOMY')  # Default to economy
            try:
                factor = EmissionFactor.objects.get(fuel_type=fuel_type)
                emissions = detail.distance_km * factor.factor_kgco2e
                return emissions
            except EmissionFactor.DoesNotExist:
                logger.warning(f"Activity {self.id}: Missing flight emission factor for {fuel_type}")
                return None

        # Hotel: nights × hotel factor
        elif detail.mode == 'HOTEL' and detail.nights:
            try:
                factor = EmissionFactor.objects.get(fuel_type='HOTEL')
                emissions = Decimal(str(detail.nights)) * factor.factor_kgco2e
                return emissions
            except EmissionFactor.DoesNotExist:
                logger.warning(f"Activity {self.id}: Missing hotel emission factor")
                return None

        # Ground transport (CAR, RAIL): spend-based fallback
        else:
            if not detail.amount_inr:
                logger.warning(f"Activity {self.id}: No amount_inr for spend-based calculation")
                return None

            try:
                factor = EmissionFactor.objects.get(fuel_type='CAR')  # Use CAR for all ground transport
                emissions = detail.amount_inr * factor.factor_kgco2e
                return emissions
            except EmissionFactor.DoesNotExist:
                logger.warning(f"Activity {self.id}: Missing CAR emission factor for spend-based calculation")
                return None

    def create_audit_log(self, action, performed_by=None, note='', **kwargs):
        """
        Helper to create audit log with snapshot.

        Args:
            action (str): Action type from AuditLog.ACTION_CHOICES
            performed_by (User|None): User performing action, None for system
            note (str): Optional note
            **kwargs: Additional AuditLog fields

        Returns:
            AuditLog instance
        """
        from apps.audit.models import AuditLog

        return AuditLog.objects.create(
            activity=self,
            activity_snapshot={
                'id': self.id,
                'category': self.category,
                'scope': self.scope,
                'period_end': self.period_end.isoformat(),
                'facility_name': self.facility.name if self.facility else None,
            },
            source_file=self.source_file,
            source_file_name=self.source_file.original_filename,
            action=action,
            performed_by=performed_by,
            note=note,
            **kwargs
        )

    def flag(self, reasons, flagged_by=None, note=''):
        """
        Flag this activity as suspicious.

        Admin users can flag manually. Ingestion may also flag rows as a
        system action, in which case flagged_by is None.

        Args:
            reasons (str or list): Flag reason code(s)
                - str: Single flag (e.g., 'unknown_plant')
                - list: Multiple flags (e.g., ['unknown_plant', 'negative_quantity'])
            flagged_by (User): Admin user performing the flag action, or None for system flags
            note (str): Optional audit log note
        """
        if flagged_by is not None and not flagged_by.is_admin():
            raise PermissionError("Only admins can flag activities")

        # Normalize to list
        if isinstance(reasons, str):
            reasons = [reasons]

        self.is_suspicious = True

        # Merge with existing flags
        if self.flag_reason:
            existing_flags = set(self.flag_reason.split('|'))
            existing_flags.update(reasons)
            self.flag_reason = '|'.join(sorted(existing_flags))
        else:
            self.flag_reason = '|'.join(sorted(reasons))

        self.status = 'FLAGGED'
        self.save()

        # Sync file counters
        self.source_file.sync_counters()

        # Create audit log
        self.create_audit_log(
            action='FLAGGED',
            performed_by=flagged_by,
            note=note or f"Flagged with reasons: {', '.join(reasons)}"
        )

    def approve_by_analyst(self, user, note=''):
        """
        Analyst approval - moves to PENDING (waiting for admin).

        Args:
            user (User): Analyst user performing the approval
            note (str): Optional note for audit log

        Raises:
            PermissionError: If user not analyst or period locked
        """
        if not user.is_analyst():
            raise PermissionError("User must have analyst role")

        # Check period lock
        from apps.core.utils import is_period_locked
        if is_period_locked(self.org, self.period_end):
            raise PermissionError(f"Period {self.period_end.strftime('%B %Y')} is locked")

        self.status = 'PENDING'
        self.save()

        # Sync file counters
        self.source_file.sync_counters()

        # Create audit log
        audit_note = note or f"Reviewed and approved by analyst {user.username}"
        self.create_audit_log(
            action='REVIEWED',
            performed_by=user,
            note=audit_note
        )

    def approve_by_admin(self, user, note=''):
        """
        Admin final approval - moves to APPROVED (final sign-off).

        Args:
            user (User): Admin user performing the approval
            note (str): Optional note for audit log

        Raises:
            PermissionError: If user not admin or period locked
        """
        from django.utils import timezone

        if not user.is_admin():
            raise PermissionError("Only admins can give final approval")

        # Check period lock
        from apps.core.utils import is_period_locked
        if is_period_locked(self.org, self.period_end):
            raise PermissionError(f"Period {self.period_end.strftime('%B %Y')} is locked")

        self.status = 'APPROVED'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

        # Sync file counters
        self.source_file.sync_counters()

        # Create audit log
        audit_note = note or f"Final approval by admin {user.username}"
        self.create_audit_log(
            action='APPROVED',
            performed_by=user,
            note=audit_note
        )

    def unflag(self, user, note=''):
        """
        Remove flag from activity. Only admins can unflag.

        Args:
            user (User): Admin user performing the unflag action
            note (str): Optional note for audit log

        Raises:
            PermissionError: If user not admin or period locked
        """
        if not user.is_admin():
            raise PermissionError("Only admins can unflag activities")

        # Check period lock
        from apps.core.utils import is_period_locked
        if is_period_locked(self.org, self.period_end):
            raise PermissionError(f"Period {self.period_end.strftime('%B %Y')} is locked")

        self.is_suspicious = False
        self.flag_reason = None
        self.status = 'FLAGGED'  # Keep in review queue for re-review
        self.save()

        # Sync file counters
        self.source_file.sync_counters()

        # Create audit log
        audit_note = note or f"Unflagged by admin {user.username}"
        self.create_audit_log(
            action='REVIEWED',
            performed_by=user,
            note=audit_note
        )


class SAPDetail(models.Model):
    """
    One-to-one with Activity for SAP MB51 material documents.
    """
    CLASSIFICATION_METHOD_CHOICES = [
        ('MATKL', 'Material Group (MATKL)'),
        ('KEYWORD', 'Keyword Match'),
        ('MEINS', 'Unit-based (MEINS)'),
        ('MANUAL', 'Manual Classification'),
        ('UNCLASSIFIED', 'Unclassified'),
    ]

    activity = models.OneToOneField(
        Activity,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='sap_detail'
    )
    plant_code = models.CharField(max_length=50, help_text="SAP WERKS")
    material_number = models.CharField(max_length=50, help_text="SAP MATNR")
    material_desc = models.CharField(max_length=255, help_text="SAP MAKTX")
    material_group = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="SAP MATKL - PRIMARY classification signal"
    )
    quantity_raw = models.DecimalField(max_digits=15, decimal_places=3, help_text="Original value")
    unit_raw = models.CharField(max_length=20, help_text="Original MEINS")
    quantity_normalized = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Converted to canonical unit"
    )
    unit_normalized = models.CharField(max_length=20, help_text="L, M3, KG, KWH, etc.")
    conversion_factor = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )
    conversion_note = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="e.g., 'GAL→L: 3.785411'"
    )
    movement_type = models.CharField(max_length=20, help_text="SAP BWART, e.g., '101'")
    vendor_number = models.CharField(max_length=50, null=True, blank=True, help_text="SAP LIFNR")
    po_number = models.CharField(max_length=50, null=True, blank=True, help_text="SAP EBELN")
    classification_method = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_METHOD_CHOICES,
        default='UNCLASSIFIED'
    )

    class Meta:
        db_table = 'sap_details'

    def __str__(self):
        return f"SAP: {self.material_number} - {self.quantity_normalized} {self.unit_normalized}"


class UtilityDetail(models.Model):
    """
    One-to-one with Activity for utility bills (TSSPDCL format).
    """
    activity = models.OneToOneField(
        Activity,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='utility_detail'
    )
    service_number = models.CharField(max_length=50, help_text="Meter ID")
    tariff_category = models.CharField(max_length=20, help_text="HT-1, LT-3, etc.")
    kwh_consumed = models.DecimalField(max_digits=12, decimal_places=3)
    unit_raw = models.CharField(max_length=10, help_text="Usually kWh, flag if kVAh")
    billing_amount_inr = models.DecimalField(max_digits=12, decimal_places=2)
    grid_emission_factor = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text="CEA 2024 factor applied"
    )
    emission_factor_source = models.CharField(max_length=50, default='CEA_2024')

    class Meta:
        db_table = 'utility_details'

    def __str__(self):
        return f"Utility: {self.service_number} - {self.kwh_consumed} kWh"


class TravelDetail(models.Model):
    """
    One-to-one with Activity for travel expense reports (Concur/Navan).
    """
    MODE_CHOICES = [
        ('AIR', 'Air'),
        ('HOTEL', 'Hotel'),
        ('CAR', 'Car'),
        ('RAIL', 'Rail'),
    ]

    CABIN_CLASS_CHOICES = [
        ('ECONOMY', 'Economy'),
        ('PREMIUM', 'Premium Economy'),
        ('BUSINESS', 'Business'),
        ('FIRST', 'First'),
    ]

    DISTANCE_METHOD_CHOICES = [
        ('GREAT_CIRCLE', 'Great Circle'),
        ('SPEND_BASED', 'Spend-based'),
    ]

    activity = models.OneToOneField(
        Activity,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='travel_detail'
    )
    trip_id = models.CharField(max_length=50, help_text="Groups related rows like outbound+hotel+return")
    employee_id = models.CharField(max_length=50)
    department = models.CharField(max_length=100, null=True, blank=True)
    cost_center = models.CharField(max_length=50, null=True, blank=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    origin = models.CharField(max_length=10, null=True, blank=True, help_text="IATA code for AIR")
    destination = models.CharField(max_length=10, null=True, blank=True, help_text="IATA code for AIR")
    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Great circle for AIR, null for HOTEL/CAR"
    )
    cabin_class = models.CharField(
        max_length=10,
        choices=CABIN_CLASS_CHOICES,
        null=True,
        blank=True
    )
    cabin_class_raw = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Original value like 'Y', 'J'"
    )
    nights = models.IntegerField(null=True, blank=True, help_text="For HOTEL mode")
    amount_raw = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    amount_inr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Converted amount in INR"
    )
    # FX traceability fields
    fx_rate_used = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Exchange rate applied for conversion (e.g., 83.250000 for 1 USD = 83.25 INR)"
    )
    fx_rate_date = models.DateField(
        null=True,
        blank=True,
        help_text="Effective date of the FX rate used"
    )
    fx_source = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Source of FX rate (e.g., 'CurrencyConversionRate:2024-01-01')"
    )
    fx_note = models.TextField(
        null=True,
        blank=True,
        help_text="Additional FX conversion notes (e.g., 'Used latest available rate')"
    )
    distance_method = models.CharField(
        max_length=20,
        choices=DISTANCE_METHOD_CHOICES,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'travel_details'

    def __str__(self):
        if self.mode == 'AIR':
            return f"Travel: {self.origin}→{self.destination} ({self.get_cabin_class_display()})"
        elif self.mode == 'HOTEL':
            return f"Travel: Hotel - {self.nights} nights"
        else:
            return f"Travel: {self.get_mode_display()}"
