from django.contrib import admin
from .models import Notification, ActionLog

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__email', 'message')

@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'details')
    list_filter = ('timestamp', 'action')
    search_fields = ('user__email', 'action', 'details')
