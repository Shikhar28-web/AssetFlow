from django.contrib import admin
from .models import MaintenanceRequest

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'asset', 'raised_by', 'priority', 'status', 'assigned_technician', 'created_at')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('asset__name', 'asset__asset_tag', 'raised_by__email', 'description')
