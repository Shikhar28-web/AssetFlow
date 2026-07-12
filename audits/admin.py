from django.contrib import admin
from .models import AuditCycle, AuditItem

@admin.register(AuditCycle)
class AuditCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'location', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('name', 'location')

@admin.register(AuditItem)
class AuditItemAdmin(admin.ModelAdmin):
    list_display = ('audit_cycle', 'asset', 'status', 'verified_at', 'verified_by')
    list_filter = ('status', 'audit_cycle')
    search_fields = ('asset__name', 'asset__asset_tag')
