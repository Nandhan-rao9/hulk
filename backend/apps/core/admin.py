from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Organization, User, Facility, PlantLookup,
    ClientMaterialGroupMapping, EmissionFactor, CurrencyConversionRate, ReportingPeriodLock
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'org', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active', 'org']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('org', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('org', 'role')}),
    )


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'org', 'created_at']
    list_filter = ['org', 'country']
    search_fields = ['name', 'city']


@admin.register(PlantLookup)
class PlantLookupAdmin(admin.ModelAdmin):
    list_display = ['code', 'source_type', 'facility', 'org']
    list_filter = ['source_type', 'org']
    search_fields = ['code', 'facility__name']


@admin.register(ClientMaterialGroupMapping)
class ClientMaterialGroupMappingAdmin(admin.ModelAdmin):
    list_display = ['matkl_code', 'fuel_type', 'scope', 'org', 'created_at']
    list_filter = ['fuel_type', 'scope', 'org']
    search_fields = ['matkl_code']


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['fuel_type', 'factor_kgco2e', 'unit', 'source', 'year']
    list_filter = ['source', 'year']
    search_fields = ['fuel_type']


@admin.register(CurrencyConversionRate)
class CurrencyConversionRateAdmin(admin.ModelAdmin):
    list_display = ['currency_code', 'rate_to_inr', 'effective_date', 'source', 'updated_at']
    list_filter = ['source', 'effective_date']
    search_fields = ['currency_code']
    ordering = ['-effective_date', 'currency_code']


@admin.register(ReportingPeriodLock)
class ReportingPeriodLockAdmin(admin.ModelAdmin):
    list_display = ['org', 'period_month', 'is_locked', 'locked_by', 'locked_at']
    list_filter = ['is_locked', 'org']
    date_hierarchy = 'period_month'
