from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Notification, ActionLog

def is_manager_or_admin(user):
    return user.is_authenticated and (user.role in ['admin', 'asset_manager'] or user.is_staff)

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications/list.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

@login_required
@user_passes_test(is_manager_or_admin)
def action_logs(request):
    logs = ActionLog.objects.all().order_by('-timestamp')
    return render(request, 'notifications/logs.html', {'logs': logs})
