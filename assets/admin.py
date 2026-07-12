from django.contrib import admin
from .models import Asset

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_tag', 'category', 'status', 'condition', 'location', 'is_shared_bookable', 'department')
    list_filter = ('status', 'condition', 'category', 'is_shared_bookable', 'department')
    search_fields = ('name', 'asset_tag', 'serial_number', 'location')
    readonly_fields = ('asset_tag',)
