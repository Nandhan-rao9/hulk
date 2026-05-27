from django.contrib import admin
from .models import Activity, SAPDetail, UtilityDetail, TravelDetail


class SAPDetailInline(admin.StackedInline):
    model = SAPDetail
    extra = 0


class UtilityDetailInline(admin.StackedInline):
    model = UtilityDetail
    extra = 0


class TravelDetailInline(admin.StackedInline):
    model = TravelDetail
    extra = 0


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'scope', 'period_end', 'facility', 'status', 'is_suspicious', 'emissions_kgco2e', 'approved_by']
    list_filter = ['status', 'scope', 'category', 'is_suspicious', 'period_end']
    search_fields = ['id', 'flag_reason', 'facility__name']
    readonly_fields = ['created_at', 'approved_at', 'raw_record']
    ordering = ['-period_end', '-created_at']
    inlines = [SAPDetailInline, UtilityDetailInline, TravelDetailInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('org', 'source_file', 'raw_record', 'facility')
        }),
        ('Classification', {
            'fields': ('scope', 'category')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end', 'is_cross_month')
        }),
        ('Status', {
            'fields': ('status', 'is_suspicious', 'flag_reason', 'approved_by', 'approved_at')
        }),
        ('Emissions', {
            'fields': ('emissions_kgco2e',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(SAPDetail)
class SAPDetailAdmin(admin.ModelAdmin):
    list_display = ['activity', 'plant_code', 'material_number', 'material_group', 'quantity_normalized', 'unit_normalized', 'classification_method']
    list_filter = ['classification_method', 'unit_normalized']
    search_fields = ['plant_code', 'material_number', 'material_desc', 'material_group']


@admin.register(UtilityDetail)
class UtilityDetailAdmin(admin.ModelAdmin):
    list_display = ['activity', 'service_number', 'tariff_category', 'kwh_consumed', 'billing_amount_inr']
    list_filter = ['tariff_category']
    search_fields = ['service_number']


@admin.register(TravelDetail)
class TravelDetailAdmin(admin.ModelAdmin):
    list_display = ['activity', 'trip_id', 'mode', 'origin', 'destination', 'cabin_class', 'distance_km']
    list_filter = ['mode', 'cabin_class', 'distance_method']
    search_fields = ['trip_id', 'employee_id', 'origin', 'destination']
