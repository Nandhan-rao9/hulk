from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    """
    Multi-tenancy root. Every record in the system belongs to one organization.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model with role-based access control.

    Roles:
    - analyst: can review, approve, and flag activities
    - admin: can lock periods, invalidate files, + all analyst permissions
    """
    ROLE_CHOICES = [
        ('analyst', 'Analyst'),
        ('admin', 'Admin'),
    ]

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,  # Nullable for superuser creation
        blank=True
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='analyst'
    )

    class Meta:
        db_table = 'users'
        ordering = ['username']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    def is_analyst(self):
        """Check if user has analyst role (or admin, since admin inherits analyst permissions)."""
        return self.role in ['analyst', 'admin']


class Facility(models.Model):
    """
    A physical location the client operates (plant, office, warehouse, etc).
    """
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='facilities')
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facilities'
        verbose_name_plural = 'facilities'
        ordering = ['name']
        unique_together = ['org', 'name']

    def __str__(self):
        return f"{self.name} ({self.city})"


class PlantLookup(models.Model):
    """
    Maps opaque codes from source files to actual facilities.
    Used for SAP plant codes (WERKS) and utility meter/service numbers.
    """
    SOURCE_TYPE_CHOICES = [
        ('SAP', 'SAP'),
        ('UTILITY', 'Utility'),
    ]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='plant_lookups')
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='plant_codes')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    code = models.CharField(max_length=100, help_text="SAP WERKS code or utility meter number")

    class Meta:
        db_table = 'plant_lookups'
        unique_together = ['org', 'source_type', 'code']
        ordering = ['source_type', 'code']

    def __str__(self):
        return f"{self.source_type}:{self.code} → {self.facility.name}"


class ClientMaterialGroupMapping(models.Model):
    """
    Maps client's SAP material group codes (MATKL) to fuel types.
    This is the PRIMARY classification signal for SAP data.
    Provided by client during onboarding.
    """
    FUEL_TYPE_CHOICES = [
        ('DIESEL', 'Diesel'),
        ('PETROL', 'Petrol'),
        ('NATGAS', 'Natural Gas'),
        ('LPG', 'LPG'),
        ('FUEL_OIL', 'Fuel Oil'),
        ('COAL', 'Coal'),
        ('KEROSENE', 'Kerosene'),
        ('ELECTRICITY', 'Electricity'),
    ]

    SCOPE_CHOICES = [
        (1, 'Scope 1'),
        (2, 'Scope 2'),
    ]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='material_mappings')
    matkl_code = models.CharField(max_length=50, help_text="SAP Material Group code")
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES)
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'client_material_group_mappings'
        unique_together = ['org', 'matkl_code']
        ordering = ['matkl_code']

    def __str__(self):
        return f"{self.matkl_code} → {self.fuel_type} (Scope {self.scope})"


class EmissionFactor(models.Model):
    """
    Hardcoded emission factors from DEFRA 2024 and CEA 2023-24.
    Never mutated after seeding. Used for all emissions calculations.
    """
    FUEL_TYPE_CHOICES = [
        ('DIESEL', 'Diesel'),
        ('PETROL', 'Petrol'),
        ('NATGAS', 'Natural Gas'),
        ('LPG', 'LPG'),
        ('FUEL_OIL', 'Fuel Oil'),
        ('COAL', 'Coal'),
        ('KEROSENE', 'Kerosene'),
        ('ELECTRICITY', 'Electricity'),
        ('FLIGHT_ECONOMY', 'Flight Economy'),
        ('FLIGHT_PREMIUM', 'Flight Premium Economy'),
        ('FLIGHT_BUSINESS', 'Flight Business'),
        ('FLIGHT_FIRST', 'Flight First'),
        ('HOTEL', 'Hotel'),
        ('CAR', 'Car (spend-based)'),
    ]

    fuel_type = models.CharField(max_length=30, choices=FUEL_TYPE_CHOICES, unique=True)
    unit = models.CharField(max_length=10, help_text="L, M3, KG, KWH, KM, NIGHT, INR")
    factor_kgco2e = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text="Emission factor in kgCO2e per unit"
    )
    source = models.CharField(max_length=50, help_text="DEFRA_2024, CEA_2024")
    year = models.IntegerField(default=2024)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'emission_factors'
        ordering = ['fuel_type']

    def __str__(self):
        return f"{self.fuel_type}: {self.factor_kgco2e} kgCO2e/{self.unit}"


class ReportingPeriodLock(models.Model):
    """
    Tracks which reporting periods (months) are locked per organization.
    Once locked, no edits allowed to activities in that period.
    """
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='period_locks')
    period_month = models.DateField(help_text="First day of the month (e.g., 2024-01-01)")
    locked_by = models.CharField(max_length=255)
    locked_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=True)
    unlocked_by = models.CharField(max_length=255, blank=True, null=True)
    unlocked_at = models.DateTimeField(blank=True, null=True)
    unlock_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'reporting_period_locks'
        unique_together = ['org', 'period_month']
        ordering = ['-period_month']

    def __str__(self):
        status = "Locked" if self.is_locked else "Unlocked"
        return f"{self.org.name} - {self.period_month.strftime('%B %Y')} ({status})"
