from django.contrib import admin
from .models import ResourceBooking

@admin.register(ResourceBooking)
class ResourceBookingAdmin(admin.ModelAdmin):
    list_display = ('asset', 'booked_by', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('asset__name', 'asset__asset_tag', 'booked_by__email')
