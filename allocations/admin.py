from django.contrib import admin
from .models import Allocation, TransferRequest

@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ('asset', 'assignee', 'department', 'allocated_by', 'allocated_at', 'expected_return_date', 'status')
    list_filter = ('status', 'allocated_at', 'expected_return_date')
    search_fields = ('asset__name', 'asset__asset_tag', 'assignee__email', 'department__name')

@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = ('asset', 'current_holder', 'target_holder', 'requested_by', 'requested_at', 'status')
    list_filter = ('status', 'requested_at')
    search_fields = ('asset__name', 'asset__asset_tag', 'current_holder__email', 'target_holder__email')
