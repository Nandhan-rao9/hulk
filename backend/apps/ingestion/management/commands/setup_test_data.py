"""
Management command to set up test data for ingestion testing.

Creates:
- Organization
- Admin user
- Facilities
- Plant lookups
- Material group mappings
- Emission factors
"""
from django.core.management.base import BaseCommand
from apps.core.models import (
    Organization, User, Facility, PlantLookup,
    ClientMaterialGroupMapping, EmissionFactor
)


class Command(BaseCommand):
    help = 'Set up test data for ingestion'

    def handle(self, *args, **options):
        # Create organization
        org, created = Organization.objects.get_or_create(
            slug='demo',
            defaults={'name': 'Demo Corporation'}
        )
        self.stdout.write(f"Organization: {org.name} ({'created' if created else 'exists'})")

        # Create admin user
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@demo.com',
                'org': org,
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
        self.stdout.write(f"User: {user.username} ({'created' if created else 'exists'})")

        # Create facilities
        facilities = [
            {'name': 'Hyderabad Plant', 'city': 'Hyderabad', 'country': 'India'},
            {'name': 'Mumbai Plant', 'city': 'Mumbai', 'country': 'India'},
            {'name': 'Bangalore Plant', 'city': 'Bangalore', 'country': 'India'},
            {'name': 'Chennai Plant', 'city': 'Chennai', 'country': 'India'},
            {'name': 'Pune Plant', 'city': 'Pune', 'country': 'India'},
        ]

        facility_objs = []
        for idx, fac_data in enumerate(facilities, start=1):
            fac, created = Facility.objects.get_or_create(
                org=org,
                name=fac_data['name'],
                defaults=fac_data
            )
            facility_objs.append(fac)
            self.stdout.write(f"  Facility: {fac.name} ({'created' if created else 'exists'})")

        # Create plant lookups (SAP codes)
        plant_codes = [
            ('1001', facility_objs[0]),  # Hyderabad
            ('1002', facility_objs[1]),  # Mumbai
            ('1003', facility_objs[2]),  # Bangalore
            ('1004', facility_objs[3]),  # Chennai
            ('1005', facility_objs[4]),  # Pune
        ]

        for code, facility in plant_codes:
            lookup, created = PlantLookup.objects.get_or_create(
                org=org,
                source_type='SAP',
                code=code,
                defaults={'facility': facility}
            )
            self.stdout.write(f"  PlantLookup: SAP:{code} -> {facility.name} ({'created' if created else 'exists'})")

        # Create utility meter lookups
        utility_meters = [
            ('550012345', facility_objs[0]),  # Hyderabad
            ('550012346', facility_objs[1]),  # Mumbai
            ('550012347', facility_objs[2]),  # Bangalore
            ('550012348', facility_objs[3]),  # Chennai
            ('550012349', facility_objs[4]),  # Pune
            ('550012350', facility_objs[0]),  # Hyderabad (2nd meter)
            ('550012351', facility_objs[1]),  # Mumbai (2nd meter)
            # UNKNOWN-9999 intentionally not added (for testing unknown meter flag)
        ]

        for meter, facility in utility_meters:
            lookup, created = PlantLookup.objects.get_or_create(
                org=org,
                source_type='UTILITY',
                code=meter,
                defaults={'facility': facility}
            )
            self.stdout.write(f"  PlantLookup: UTILITY:{meter} -> {facility.name} ({'created' if created else 'exists'})")

        # Create material group mappings
        mappings = [
            ('FUEL-LQ', 'DIESEL', 1),
            ('GAS-NG', 'NATGAS', 1),
            ('GAS-LPG', 'LPG', 1),
            ('FUEL-OIL', 'FUEL_OIL', 1),
            ('COAL-BIT', 'COAL', 1),
            ('KERO-JET', 'KEROSENE', 1),
            ('ELEC-GR', 'ELECTRICITY', 2),
        ]

        for matkl, fuel_type, scope in mappings:
            mapping, created = ClientMaterialGroupMapping.objects.get_or_create(
                org=org,
                matkl_code=matkl,
                defaults={'fuel_type': fuel_type, 'scope': scope}
            )
            self.stdout.write(f"  MaterialMapping: {matkl} -> {fuel_type} Scope {scope} ({'created' if created else 'exists'})")

        # Create emission factors
        factors = [
            ('DIESEL', 'L', 2.68, 'DEFRA_2024'),
            ('PETROL', 'L', 2.31, 'DEFRA_2024'),
            ('NATGAS', 'M3', 2.03, 'DEFRA_2024'),
            ('LPG', 'KG', 2.98, 'DEFRA_2024'),
            ('FUEL_OIL', 'L', 3.18, 'DEFRA_2024'),
            ('COAL', 'KG', 2.42, 'DEFRA_2024'),
            ('KEROSENE', 'L', 2.52, 'DEFRA_2024'),
            ('ELECTRICITY', 'KWH', 0.716, 'CEA_2024'),
        ]

        for fuel_type, unit, factor, source in factors:
            ef, created = EmissionFactor.objects.get_or_create(
                fuel_type=fuel_type,
                defaults={
                    'unit': unit,
                    'factor_kgco2e': factor,
                    'source': source,
                    'year': 2024
                }
            )
            self.stdout.write(f"  EmissionFactor: {fuel_type} = {factor} kgCO2e/{unit} ({'created' if created else 'exists'})")

        self.stdout.write(self.style.SUCCESS('\nTest data setup complete!'))
        self.stdout.write(f"\nYou can now test with:")
        self.stdout.write(f"  python manage.py ingest_file sample_data/sap_mb51_export.csv --source-type SAP --org-slug demo")
