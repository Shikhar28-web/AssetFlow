from notifications.models import Notification

def notifications(request):
    """Make unread notification count and list available to every template."""
    if request.user.is_authenticated:
        user_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
        return {'user_notifications': user_notifications}
    return {'user_notifications': []}
