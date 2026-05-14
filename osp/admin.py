from django.contrib import admin

from .models import (
    Equipment,
    Firefighter,
    PersonnelResource,
    Request,
    RequestResponse,
    RescueAuditLog,
    RescueMessage,
    RescueOperation,
    SisAuditLog,
    Unit,
    OSPReport,
    FuelUsage,
    VehicleInsurance,
    FirefighterTest,
    EquipmentMaintenance,
    TrainingRecord,
)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name',)


@admin.register(Firefighter)
class FirefighterAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'unit', 'rank', 'created_at')
    list_filter = ('unit', 'rank')
    search_fields = ('first_name', 'last_name')


class RequestResponseInline(admin.TabularInline):
    model = RequestResponse
    extra = 0


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'unit', 'status', 'created_at', 'updated_at', 'signed_at', 'archived_at')
    list_filter = ('status', 'unit')
    search_fields = ('title', 'description')
    inlines = [RequestResponseInline]


@admin.register(RequestResponse)
class RequestResponseAdmin(admin.ModelAdmin):
    list_display = ('request', 'action', 'responder', 'created_at')
    list_filter = ('action',)
    search_fields = ('message',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'category', 'inventory_number', 'condition', 'inspection_valid_until')
    list_filter = ('unit', 'condition', 'category')
    search_fields = ('name', 'inventory_number')


@admin.register(PersonnelResource)
class PersonnelResourceAdmin(admin.ModelAdmin):
    list_display = ('unit', 'firefighter', 'role_name', 'readiness', 'updated_at')
    list_filter = ('unit', 'readiness')
    search_fields = ('role_name', 'qualifications')


@admin.register(SisAuditLog)
class SisAuditLogAdmin(admin.ModelAdmin):
    list_display = ('unit', 'request', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'unit')
    search_fields = ('message',)


class RescueMessageInline(admin.TabularInline):
    model = RescueMessage
    extra = 0


@admin.register(RescueOperation)
class RescueOperationAdmin(admin.ModelAdmin):
    list_display = ('title', 'unit', 'incident_type', 'priority', 'status', 'occurred_at', 'updated_at')
    list_filter = ('status', 'priority', 'unit', 'incident_type')
    search_fields = ('title', 'location', 'description', 'final_report')
    inlines = [RescueMessageInline]


@admin.register(RescueMessage)
class RescueMessageAdmin(admin.ModelAdmin):
    list_display = ('operation', 'sender_type', 'kind', 'author', 'created_at')
    list_filter = ('sender_type', 'kind')
    search_fields = ('message',)


@admin.register(RescueAuditLog)
class RescueAuditLogAdmin(admin.ModelAdmin):
    list_display = ('operation', 'unit', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'unit')
    search_fields = ('message',)


# ==================== OSP REPORTING ADMIN ====================


class FuelUsageInline(admin.TabularInline):
    model = FuelUsage
    extra = 1
    fields = ('date', 'equipment', 'liters', 'unit_price', 'total_cost', 'notes')
    readonly_fields = ('total_cost',)


@admin.register(OSPReport)
class OSPReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'unit', 'report_start_date', 'report_end_date', 'status', 'created_at')
    list_filter = ('status', 'unit', 'report_start_date')
    search_fields = ('title', 'description')
    inlines = [FuelUsageInline]
    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('unit', 'title', 'description', 'report_start_date', 'report_end_date')
        }),
        ('Status', {
            'fields': ('status', 'created_by', 'created_at')
        }),
        ('Zatwierdzenie', {
            'fields': ('submitted_by', 'submitted_at', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FuelUsage)
class FuelUsageAdmin(admin.ModelAdmin):
    list_display = ('report', 'equipment', 'date', 'liters', 'unit_price', 'total_cost')
    list_filter = ('report', 'date')
    search_fields = ('equipment__name',)
    readonly_fields = ('total_cost',)


@admin.register(VehicleInsurance)
class VehicleInsuranceAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'registration_number', 'insurance_provider', 'policy_end_date')
    list_filter = ('unit', 'policy_end_date')
    search_fields = ('registration_number', 'vin', 'policy_number')


@admin.register(FirefighterTest)
class FirefighterTestAdmin(admin.ModelAdmin):
    list_display = ('firefighter', 'test_type', 'test_name', 'test_date', 'expiration_date', 'result')
    list_filter = ('test_type', 'result', 'test_date')
    search_fields = ('firefighter__first_name', 'firefighter__last_name', 'test_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'maintenance_type', 'status', 'scheduled_date', 'completed_date', 'cost')
    list_filter = ('maintenance_type', 'status', 'scheduled_date')
    search_fields = ('equipment__name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('firefighter', 'training_name', 'training_date', 'duration_hours', 'status', 'certification_expiration')
    list_filter = ('status', 'training_date', 'certification_expiration')
    search_fields = ('firefighter__first_name', 'firefighter__last_name', 'training_name')
    readonly_fields = ('created_at', 'updated_at')
