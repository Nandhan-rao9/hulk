"""
Management command to create clean demo database.
Usage: python manage.py seed_clean_demo
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.core.models import (
    Organization, User, Facility, PlantLookup,
    ClientMaterialGroupMapping, EmissionFactor, CurrencyConversionRate
)
from apps.ingestion.models import SourceFile, RawRecord
from apps.activities.models import Activity, SAPDetail, UtilityDetail, TravelDetail
from apps.audit.models import AuditLog
from decimal import Decimal
from datetime import date

class Command(BaseCommand):
    help = 'Create clean demo database with 2 orgs, 4 users, and lookup tables'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('[WARNING] This will DELETE ALL DATA and create fresh demo data!'))
        self.stdout.write(self.style.WARNING('Press Ctrl+C to cancel, or wait 3 seconds...'))

        import time
        time.sleep(3)

        with transaction.atomic():
            self.stdout.write('[1/6] Clearing all data...')
            self._clear_all_data()

            self.stdout.write('[2/6] Creating organizations...')
            org1, org2 = self._create_organizations()

            self.stdout.write('[3/6] Creating users...')
            users = self._create_users(org1, org2)

            self.stdout.write('[4/6] Creating facilities...')
            self._create_facilities(org1, org2)

            self.stdout.write('[5/6] Creating lookup tables...')
            self._create_lookups(org1, org2)

            self.stdout.write('[6/6] Creating emission factors & currency rates...')
            self._create_emission_factors()
            self._create_currency_rates()

            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Demo database created successfully!\n'))
            self._print_summary(users)

    def _clear_all_data(self):
        """Delete all data from all tables."""
        AuditLog.objects.all().delete()
        TravelDetail.objects.all().delete()
        UtilityDetail.objects.all().delete()
        SAPDetail.objects.all().delete()
        Activity.objects.all().delete()
        RawRecord.objects.all().delete()
        SourceFile.objects.all().delete()
        CurrencyConversionRate.objects.all().delete()
        EmissionFactor.objects.all().delete()
        ClientMaterialGroupMapping.objects.all().delete()
        PlantLookup.objects.all().delete()
        Facility.objects.all().delete()
        User.objects.all().delete()
        Organization.objects.all().delete()

    def _create_organizations(self):
        """Create 2 organizations."""
        org1 = Organization.objects.create(
            name='Acme Manufacturing Ltd',
            slug='acme-manufacturing'
        )

        org2 = Organization.objects.create(
            name='TechCorp Industries',
            slug='techcorp-industries'
        )

        return org1, org2

    def _create_users(self, org1, org2):
        """Create 4 users: 1 admin + 1 analyst per org."""
        users = []

        # Org 1 - Acme Manufacturing
        admin1 = User.objects.create_user(
            username='acme_admin',
            email='admin@acme.com',
            password='admin123',
            first_name='Sarah',
            last_name='Admin',
            org=org1,
            role='admin'
        )
        users.append(admin1)

        analyst1 = User.objects.create_user(
            username='acme_analyst',
            email='analyst@acme.com',
            password='analyst123',
            first_name='John',
            last_name='Analyst',
            org=org1,
            role='analyst'
        )
        users.append(analyst1)

        # Org 2 - TechCorp Industries
        admin2 = User.objects.create_user(
            username='tech_admin',
            email='admin@techcorp.com',
            password='admin123',
            first_name='Michael',
            last_name='Admin',
            org=org2,
            role='admin'
        )
        users.append(admin2)

        analyst2 = User.objects.create_user(
            username='tech_analyst',
            email='analyst@techcorp.com',
            password='analyst123',
            first_name='Emma',
            last_name='Analyst',
            org=org2,
            role='analyst'
        )
        users.append(analyst2)

        return users

    def _create_facilities(self, org1, org2):
        """Create facilities for both orgs."""
        # Acme Manufacturing facilities
        Facility.objects.create(
            org=org1,
            name='Acme Plant Mumbai',
            city='Mumbai',
            country='India'
        )
        Facility.objects.create(
            org=org1,
            name='Acme Plant Pune',
            city='Pune',
            country='India'
        )
        Facility.objects.create(
            org=org1,
            name='Acme Warehouse Delhi',
            city='Delhi',
            country='India'
        )

        # TechCorp facilities
        Facility.objects.create(
            org=org2,
            name='TechCorp HQ Bangalore',
            city='Bangalore',
            country='India'
        )
        Facility.objects.create(
            org=org2,
            name='TechCorp Factory Chennai',
            city='Chennai',
            country='India'
        )

    def _create_lookups(self, org1, org2):
        """Create lookup tables for both orgs."""
        # Acme Manufacturing lookups
        acme_mumbai = Facility.objects.get(org=org1, name='Acme Plant Mumbai')
        acme_pune = Facility.objects.get(org=org1, name='Acme Plant Pune')
        acme_delhi = Facility.objects.get(org=org1, name='Acme Warehouse Delhi')

        # Plant lookups for Acme
        PlantLookup.objects.create(org=org1, facility=acme_mumbai, source_type='SAP', code='1000')
        PlantLookup.objects.create(org=org1, facility=acme_pune, source_type='SAP', code='2000')
        PlantLookup.objects.create(org=org1, facility=acme_delhi, source_type='SAP', code='3000')
        PlantLookup.objects.create(org=org1, facility=acme_mumbai, source_type='UTILITY', code='MH-METER-001')
        PlantLookup.objects.create(org=org1, facility=acme_pune, source_type='UTILITY', code='MH-METER-002')

        # Material mappings for Acme
        ClientMaterialGroupMapping.objects.create(org=org1, matkl_code='FUEL-01', fuel_type='DIESEL', scope=1)
        ClientMaterialGroupMapping.objects.create(org=org1, matkl_code='FUEL-02', fuel_type='PETROL', scope=1)
        ClientMaterialGroupMapping.objects.create(org=org1, matkl_code='FUEL-03', fuel_type='LPG', scope=1)
        ClientMaterialGroupMapping.objects.create(org=org1, matkl_code='GAS-01', fuel_type='NATGAS', scope=1)

        # TechCorp lookups
        tech_blr = Facility.objects.get(org=org2, name='TechCorp HQ Bangalore')
        tech_chennai = Facility.objects.get(org=org2, name='TechCorp Factory Chennai')

        # Plant lookups for TechCorp
        PlantLookup.objects.create(org=org2, facility=tech_blr, source_type='SAP', code='BLR-001')
        PlantLookup.objects.create(org=org2, facility=tech_chennai, source_type='SAP', code='CHN-001')
        PlantLookup.objects.create(org=org2, facility=tech_blr, source_type='UTILITY', code='KA-METER-100')
        PlantLookup.objects.create(org=org2, facility=tech_chennai, source_type='UTILITY', code='TN-METER-200')

        # Material mappings for TechCorp
        ClientMaterialGroupMapping.objects.create(org=org2, matkl_code='DIESEL', fuel_type='DIESEL', scope=1)
        ClientMaterialGroupMapping.objects.create(org=org2, matkl_code='PETROL', fuel_type='PETROL', scope=1)
        ClientMaterialGroupMapping.objects.create(org=org2, matkl_code='ELEC', fuel_type='ELECTRICITY', scope=2)
        ClientMaterialGroupMapping.objects.create(org=org2, matkl_code='GAS', fuel_type='NATGAS', scope=1)

    def _create_emission_factors(self):
        """Create standard emission factors (DEFRA 2024)."""
        factors = [
            ('DIESEL', 'L', Decimal('2.687'), 'DEFRA_2024'),
            ('PETROL', 'L', Decimal('2.315'), 'DEFRA_2024'),
            ('NATGAS', 'M3', Decimal('2.019'), 'DEFRA_2024'),
            ('LPG', 'KG', Decimal('2.983'), 'DEFRA_2024'),
            ('FUEL_OIL', 'L', Decimal('3.179'), 'DEFRA_2024'),
            ('COAL', 'KG', Decimal('2.419'), 'DEFRA_2024'),
            ('KEROSENE', 'L', Decimal('2.537'), 'DEFRA_2024'),
            ('ELECTRICITY', 'KWH', Decimal('0.716'), 'CEA_2024'),
            ('FLIGHT_ECONOMY', 'KM', Decimal('0.133'), 'DEFRA_2024'),
            ('FLIGHT_PREMIUM', 'KM', Decimal('0.201'), 'DEFRA_2024'),
            ('FLIGHT_BUSINESS', 'KM', Decimal('0.390'), 'DEFRA_2024'),
            ('FLIGHT_FIRST', 'KM', Decimal('0.599'), 'DEFRA_2024'),
            ('HOTEL', 'NIGHT', Decimal('15.500'), 'DEFRA_2024'),
            ('CAR', 'INR', Decimal('0.150'), 'DEFRA_2024'),
        ]

        for fuel_type, unit, factor, source in factors:
            EmissionFactor.objects.create(
                fuel_type=fuel_type,
                unit=unit,
                factor_kgco2e=factor,
                source=source,
                year=2024
            )

    def _create_currency_rates(self):
        """Create currency conversion rates."""
        rates = [
            ('USD', Decimal('83.25'), date(2024, 1, 1)),
            ('EUR', Decimal('91.50'), date(2024, 1, 1)),
            ('GBP', Decimal('105.75'), date(2024, 1, 1)),
            ('SGD', Decimal('62.30'), date(2024, 1, 1)),
            ('AED', Decimal('22.65'), date(2024, 1, 1)),
            ('INR', Decimal('1.00'), date(2024, 1, 1)),
        ]

        for currency, rate, eff_date in rates:
            CurrencyConversionRate.objects.create(
                currency_code=currency,
                rate_to_inr=rate,
                effective_date=eff_date,
                source='RBI'
            )

    def _print_summary(self, users):
        """Print summary of created data."""
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('DATABASE CREDENTIALS'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('ORGANIZATION 1: Acme Manufacturing Ltd'))
        self.stdout.write(f'   Admin:    username: acme_admin    password: admin123')
        self.stdout.write(f'   Analyst:  username: acme_analyst  password: analyst123')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('ORGANIZATION 2: TechCorp Industries'))
        self.stdout.write(f'   Admin:    username: tech_admin    password: admin123')
        self.stdout.write(f'   Analyst:  username: tech_analyst  password: analyst123')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'[OK] Organizations: {Organization.objects.count()}')
        self.stdout.write(f'[OK] Users: {User.objects.count()}')
        self.stdout.write(f'[OK] Facilities: {Facility.objects.count()}')
        self.stdout.write(f'[OK] Plant Lookups: {PlantLookup.objects.count()}')
        self.stdout.write(f'[OK] Material Mappings: {ClientMaterialGroupMapping.objects.count()}')
        self.stdout.write(f'[OK] Emission Factors: {EmissionFactor.objects.count()}')
        self.stdout.write(f'[OK] Currency Rates: {CurrencyConversionRate.objects.count()}')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('NEXT STEPS:'))
        self.stdout.write('1. Run: python generate_sample_excels.py')
        self.stdout.write('2. Upload Excel files from sample_uploads/')
        self.stdout.write('3. Log in with any of the credentials above')
        self.stdout.write('4. Test the workflow!')
        self.stdout.write('')
