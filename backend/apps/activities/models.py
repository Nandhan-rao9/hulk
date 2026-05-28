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
        ('PENDING', 'Pending'),
        ('FLAGGED', 'Flagged'),
        ('APPROVED', 'Approved'),
        ('LOCKED', 'Locked'),
        ('INVALIDATED', 'Invalidated'),
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
        help_text="Calculated emissions in kgCO2e"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
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

    def flag(self, reasons):
        """
        Flag this activity as suspicious.

        Args:
            reasons (str or list): Flag reason code(s)
                - str: Single flag (e.g., 'unknown_plant')
                - list: Multiple flags (e.g., ['unknown_plant', 'negative_quantity'])
        """
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

        if self.status == 'PENDING':
            self.status = 'FLAGGED'

        self.save()

    def approve(self, user, note=''):
        """
        Approve this activity.

        Args:
            user (User): User performing the approval
            note (str): Optional note for audit log
        """
        from django.utils import timezone
        self.status = 'APPROVED'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

        # Create audit log
        from apps.audit.models import AuditLog
        audit_note = note or f"Approved by {user.username}"
        AuditLog.objects.create(
            activity=self,
            source_file=self.source_file,
            action='APPROVED',
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
    plant_code = models.CharField(max_length=10, help_text="SAP WERKS")
    material_number = models.CharField(max_length=50, help_text="SAP MATNR")
    material_desc = models.CharField(max_length=255, help_text="SAP MAKTX")
    material_group = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="SAP MATKL - PRIMARY classification signal"
    )
    quantity_raw = models.DecimalField(max_digits=15, decimal_places=3, help_text="Original value")
    unit_raw = models.CharField(max_length=10, help_text="Original MEINS")
    quantity_normalized = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Converted to canonical unit"
    )
    unit_normalized = models.CharField(max_length=10, help_text="L, M3, KG, KWH, etc.")
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
    movement_type = models.CharField(max_length=10, help_text="SAP BWART, e.g., '101'")
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
