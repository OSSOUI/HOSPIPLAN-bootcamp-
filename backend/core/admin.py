from django.contrib import admin

from django.contrib import admin
from .models import (
    Staff, Role, StaffRole, Specialty, StaffSpecialty,
    Certification, CertificationDependency, StaffCertification,
    ContractType, Contract, AbsenceType, Absence, Preference,
    Service, CareUnit, ServiceStatus, StaffServiceAssignment,
    PatientLoad, StaffLoan,
    ShiftType, Shift, ShiftRequiredCertification, ShiftAssignment,
    Rule,
)


class StaffRoleInline(admin.TabularInline):
    model = StaffRole
    extra = 1


class StaffCertificationInline(admin.TabularInline):
    model = StaffCertification
    extra = 0


class ContractInline(admin.TabularInline):
    model = Contract
    extra = 0


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['first_name', 'last_name', 'email']
    inlines = [StaffRoleInline, StaffCertificationInline, ContractInline]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(ContractType)
class ContractTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_hours_per_week', 'night_shift_allowed']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager', 'bed_capacity', 'criticality_level']


@admin.register(CareUnit)
class CareUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'service']
    list_filter = ['service']


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_hours', 'requires_rest_after']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['shift_type', 'care_unit', 'start_datetime', 'end_datetime', 'min_staff']
    list_filter = ['shift_type', 'care_unit__service']


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'shift', 'assigned_at']


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'absence_type', 'start_date', 'expected_end_date', 'is_planned']
    list_filter = ['absence_type', 'is_planned']


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'value', 'unit', 'valid_from', 'valid_to']


# Enregistrement simple des autres modèles
admin.site.register(StaffRole)
admin.site.register(StaffSpecialty)
admin.site.register(CertificationDependency)
admin.site.register(StaffCertification)
admin.site.register(Contract)
admin.site.register(AbsenceType)
admin.site.register(Preference)
admin.site.register(ServiceStatus)
admin.site.register(StaffServiceAssignment)
admin.site.register(PatientLoad)
admin.site.register(StaffLoan)
admin.site.register(ShiftRequiredCertification)
