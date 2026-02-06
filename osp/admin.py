from django.contrib import admin

try:
    # django-unfold provides drop-in replacements for admin classes
    from unfold.admin import ModelAdmin, TabularInline
except Exception:  # fallback if unfold not installed
    ModelAdmin = admin.ModelAdmin
    TabularInline = admin.TabularInline

from .models import Unit, Firefighter, Request, RequestResponse


@admin.register(Unit)
class UnitAdmin(ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name',)


@admin.register(Firefighter)
class FirefighterAdmin(ModelAdmin):
    list_display = ('first_name', 'last_name', 'unit', 'rank', 'created_at')
    list_filter = ('unit', 'rank')
    search_fields = ('first_name', 'last_name')


class RequestResponseInline(TabularInline):
    model = RequestResponse
    extra = 0


@admin.register(Request)
class RequestAdmin(ModelAdmin):
    list_display = ('title', 'unit', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'unit')
    search_fields = ('title', 'description')
    inlines = [RequestResponseInline]


@admin.register(RequestResponse)
class RequestResponseAdmin(ModelAdmin):
    list_display = ('request', 'action', 'responder', 'created_at')
    list_filter = ('action',)
    search_fields = ('message',)
