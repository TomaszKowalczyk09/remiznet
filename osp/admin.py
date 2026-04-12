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
