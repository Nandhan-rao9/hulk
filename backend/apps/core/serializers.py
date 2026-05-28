from rest_framework import serializers
from .models import User, Organization, PlantLookup, ClientMaterialGroupMapping, Facility


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug']


class UserSerializer(serializers.ModelSerializer):
    org = OrganizationSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role', 'org']


class PlantLookupUploadSerializer(serializers.Serializer):
    """
    Serializer for plant lookup CSV upload.

    Expected CSV format:
    source_type,code,facility_name,city,country
    SAP,1000,Mumbai Plant,Mumbai,India
    UTILITY,12345678,Mumbai Plant,Mumbai,India
    """
    file = serializers.FileField(help_text="CSV file with plant lookup mappings")

    def validate_file(self, value):
        """Validate uploaded file."""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV file (.csv extension)")

        max_size = 10 * 1024 * 1024  # 10MB limit
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds 10MB limit")

        return value

    def create(self, validated_data):
        """
        Process plant lookup CSV upload.

        Returns dict with:
        - status: 'success' or 'error'
        - total_rows: int
        - created: int
        - updated: int
        - skipped: int
        - errors: list of {row, field, error}
        """
        import csv
        import io
        from django.db import transaction

        file_obj = validated_data['file']
        user = self.context['request'].user
        org = user.org

        if not org:
            raise serializers.ValidationError("User must be assigned to an organization")

        # Parse CSV
        content = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        rows = []
        errors = []
        row_num = 1  # Header is row 0

        for row in reader:
            row_num += 1

            # Validate required fields
            source_type = (row.get('source_type') or '').strip().upper()
            code = (row.get('code') or '').strip()
            facility_name = (row.get('facility_name') or '').strip()
            city = (row.get('city') or '').strip()
            country = (row.get('country') or '').strip()

            if not source_type:
                errors.append({'row': row_num, 'field': 'source_type', 'error': 'Required field missing'})
                continue
            if source_type not in ['SAP', 'UTILITY']:
                errors.append({'row': row_num, 'field': 'source_type', 'error': f'Invalid value: {source_type} (must be SAP or UTILITY)'})
                continue
            if not code:
                errors.append({'row': row_num, 'field': 'code', 'error': 'Required field missing'})
                continue
            if not facility_name:
                errors.append({'row': row_num, 'field': 'facility_name', 'error': 'Required field missing'})
                continue

            rows.append({
                'source_type': source_type,
                'code': code,
                'facility_name': facility_name,
                'city': city,
                'country': country,
            })

        # If validation errors, return immediately
        if errors:
            return {
                'status': 'error',
                'total_rows': row_num - 1,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': errors
            }

        # Apply changes in transaction
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for row_data in rows:
                # Get or create facility
                facility, facility_created = Facility.objects.get_or_create(
                    org=org,
                    name=row_data['facility_name'],
                    defaults={
                        'city': row_data['city'] or 'Unknown',
                        'country': row_data['country'] or 'Unknown',
                    }
                )

                # Get or create plant lookup
                lookup, lookup_created = PlantLookup.objects.get_or_create(
                    org=org,
                    source_type=row_data['source_type'],
                    code=row_data['code'],
                    defaults={'facility': facility}
                )

                if lookup_created:
                    created_count += 1
                else:
                    # Update facility if changed
                    if lookup.facility != facility:
                        lookup.facility = facility
                        lookup.save()
                        updated_count += 1

        return {
            'status': 'success',
            'total_rows': len(rows),
            'created': created_count,
            'updated': updated_count,
            'skipped': 0,
            'errors': []
        }


class MaterialMappingUploadSerializer(serializers.Serializer):
    """
    Serializer for material group mapping CSV upload.

    Expected CSV format:
    matkl_code,fuel_type,scope
    DIESEL01,DIESEL,1
    PETROL02,PETROL,1
    """
    file = serializers.FileField(help_text="CSV file with material group mappings")

    def validate_file(self, value):
        """Validate uploaded file."""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV file (.csv extension)")

        max_size = 10 * 1024 * 1024  # 10MB limit
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds 10MB limit")

        return value

    def create(self, validated_data):
        """
        Process material mapping CSV upload.

        Returns dict with:
        - status: 'success' or 'error'
        - total_rows: int
        - created: int
        - updated: int
        - skipped: int
        - errors: list of {row, field, error}
        """
        import csv
        import io
        from django.db import transaction

        file_obj = validated_data['file']
        user = self.context['request'].user
        org = user.org

        if not org:
            raise serializers.ValidationError("User must be assigned to an organization")

        # Valid fuel types
        VALID_FUEL_TYPES = dict(ClientMaterialGroupMapping.FUEL_TYPE_CHOICES).keys()

        # Parse CSV
        content = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        rows = []
        errors = []
        row_num = 1  # Header is row 0

        for row in reader:
            row_num += 1

            # Validate required fields
            matkl_code = (row.get('matkl_code') or '').strip()
            fuel_type = (row.get('fuel_type') or '').strip().upper()
            scope_str = (row.get('scope') or '').strip()

            if not matkl_code:
                errors.append({'row': row_num, 'field': 'matkl_code', 'error': 'Required field missing'})
                continue
            if not fuel_type:
                errors.append({'row': row_num, 'field': 'fuel_type', 'error': 'Required field missing'})
                continue
            if fuel_type not in VALID_FUEL_TYPES:
                errors.append({'row': row_num, 'field': 'fuel_type', 'error': f'Invalid fuel type: {fuel_type}'})
                continue
            if not scope_str:
                errors.append({'row': row_num, 'field': 'scope', 'error': 'Required field missing'})
                continue

            try:
                scope = int(scope_str)
                if scope not in [1, 2]:
                    raise ValueError()
            except ValueError:
                errors.append({'row': row_num, 'field': 'scope', 'error': f'Invalid scope: {scope_str} (must be 1 or 2)'})
                continue

            rows.append({
                'matkl_code': matkl_code,
                'fuel_type': fuel_type,
                'scope': scope,
            })

        # If validation errors, return immediately
        if errors:
            return {
                'status': 'error',
                'total_rows': row_num - 1,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': errors
            }

        # Apply changes in transaction
        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for row_data in rows:
                # Check if mapping already exists
                existing = ClientMaterialGroupMapping.objects.filter(
                    org=org,
                    matkl_code=row_data['matkl_code']
                ).first()

                if existing:
                    # Mapping already exists - error (user requirement: don't update)
                    errors.append({
                        'row': rows.index(row_data) + 2,  # +2 for header and 0-indexing
                        'field': 'matkl_code',
                        'error': f'Mapping for {row_data["matkl_code"]} already exists'
                    })
                    skipped_count += 1
                else:
                    # Create new mapping
                    ClientMaterialGroupMapping.objects.create(
                        org=org,
                        **row_data
                    )
                    created_count += 1

        return {
            'status': 'error' if errors else 'success',
            'total_rows': len(rows),
            'created': created_count,
            'updated': 0,
            'skipped': skipped_count,
            'errors': errors
        }
