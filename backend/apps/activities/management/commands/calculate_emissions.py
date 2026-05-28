"""
Management command to calculate/recalculate emissions for all activities.

Usage:
    python manage.py calculate_emissions
    python manage.py calculate_emissions --only-null  # Only calculate missing emissions
    python manage.py calculate_emissions --org acme-manufacturing  # Specific org
"""

from django.core.management.base import BaseCommand
from apps.activities.models import Activity
from apps.core.models import Organization


class Command(BaseCommand):
    help = 'Calculate emissions_kgco2e for activities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-null',
            action='store_true',
            help='Only calculate for activities where emissions_kgco2e is NULL',
        )
        parser.add_argument(
            '--org',
            type=str,
            help='Organization slug (e.g., acme-manufacturing)',
        )
        parser.add_argument(
            '--source-file',
            type=int,
            help='SourceFile ID to recalculate',
        )

    def handle(self, *args, **options):
        # Build queryset
        queryset = Activity.objects.all()

        # Filter by org if specified
        if options['org']:
            try:
                org = Organization.objects.get(slug=options['org'])
                queryset = queryset.filter(org=org)
                self.stdout.write(f"Filtering by organization: {org.name}")
            except Organization.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Organization '{options['org']}' not found"))
                return

        # Filter by source file if specified
        if options['source_file']:
            queryset = queryset.filter(source_file_id=options['source_file'])
            self.stdout.write(f"Filtering by source file ID: {options['source_file']}")

        # Filter to only NULL emissions if specified
        if options['only_null']:
            queryset = queryset.filter(emissions_kgco2e__isnull=True)
            self.stdout.write("Only calculating NULL emissions")

        # Select related to avoid N+1 queries
        queryset = queryset.select_related('sap_detail', 'utility_detail', 'travel_detail')

        total = queryset.count()
        self.stdout.write(f"\nFound {total} activities to process\n")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No activities to process"))
            return

        # Process activities
        success_count = 0
        failed_count = 0

        for i, activity in enumerate(queryset, start=1):
            # Show progress every 50 activities
            if i % 50 == 0:
                self.stdout.write(f"Progress: {i}/{total} ({(i/total)*100:.1f}%)")

            # Calculate emissions
            result = activity.calculate_emissions()

            if result:
                success_count += 1
            else:
                failed_count += 1

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✓ Successfully calculated: {success_count}"))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠ Failed to calculate: {failed_count}"))
            self.stdout.write(self.style.WARNING("  (Check logs for missing emission factors or data issues)"))
        self.stdout.write("="*60 + "\n")
