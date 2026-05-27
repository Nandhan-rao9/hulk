"""
Management command to ingest CSV files.

Usage:
    python manage.py ingest_file <file_path> --source-type SAP --org-slug demo
"""
from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Organization, User
from apps.ingestion.services import IngestionService


class Command(BaseCommand):
    help = 'Ingest a CSV file into the system'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to CSV file')
        parser.add_argument(
            '--source-type',
            type=str,
            required=True,
            choices=['SAP', 'UTILITY', 'TRAVEL_CONCUR', 'TRAVEL_NAVAN'],
            help='Source type'
        )
        parser.add_argument(
            '--org-slug',
            type=str,
            required=True,
            help='Organization slug'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username of uploader (default: admin)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        source_type = options['source_type']
        org_slug = options['org_slug']
        username = options['user']

        # Get organization
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            raise CommandError(f"Organization '{org_slug}' not found")

        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

        # Open file
        try:
            with open(file_path, 'rb') as f:
                # Create file-like object with name attribute
                class FileWrapper:
                    def __init__(self, file_obj, name):
                        self.file = file_obj
                        self.name = name

                    def read(self):
                        return self.file.read()

                    def seek(self, pos):
                        return self.file.seek(pos)

                file_obj = FileWrapper(f, file_path)

                # Ingest
                self.stdout.write(f"Ingesting {file_path}...")
                service = IngestionService(file_obj, source_type, org, user)
                source_file = service.ingest()

                self.stdout.write(self.style.SUCCESS(
                    f"\nSuccess! SourceFile ID: {source_file.id}\n"
                    f"  Status: {source_file.status}\n"
                    f"  Total rows: {source_file.total_rows}\n"
                    f"  Failed rows: {source_file.failed_rows}\n"
                    f"  Flagged rows: {source_file.flagged_rows}\n"
                ))

        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        except Exception as e:
            raise CommandError(f"Ingestion failed: {str(e)}")
