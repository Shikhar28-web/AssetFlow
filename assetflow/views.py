from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from assets.models import Asset
from allocations.models import Allocation, TransferRequest
from bookings.models import ResourceBooking
from maintenance.models import MaintenanceRequest
from notifications.models import Notification, ActionLog

@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()

    # Base counts for KPI cards (accessible to Admin & Asset Managers globally, or filter by role)
    if user.role in ['admin', 'asset_manager']:
        assets_available = Asset.objects.filter(status='available').count()
        assets_allocated = Asset.objects.filter(status='allocated').count()
        maintenance_today = MaintenanceRequest.objects.filter(status__in=['approved', 'technician_assigned', 'in_progress']).count()
        active_bookings = ResourceBooking.objects.filter(status__in=['upcoming', 'ongoing']).count()
        pending_transfers = TransferRequest.objects.filter(status='pending').count()
        
        # Overdue returns (past Expected Return Date)
        overdue_allocations = Allocation.objects.filter(status='active', expected_return_date__lt=today)
        upcoming_returns_count = Allocation.objects.filter(status='active', expected_return_date__gte=today).count()
        
        recent_bookings = ResourceBooking.objects.all().order_by('-created_at')[:5]
        recent_maintenance = MaintenanceRequest.objects.all().order_by('-created_at')[:5]
        
    elif user.role == 'department_head' and user.department:
        # Filter details by department
        dept = user.department
        assets_available = Asset.objects.filter(status='available').count() # global available
        assets_allocated = Asset.objects.filter(status='allocated', department=dept).count()
        maintenance_today = MaintenanceRequest.objects.filter(status__in=['approved', 'technician_assigned', 'in_progress'], asset__department=dept).count()
        active_bookings = ResourceBooking.objects.filter(status__in=['upcoming', 'ongoing'], booked_by__department=dept).count()
        pending_transfers = TransferRequest.objects.filter(status='pending', current_holder__department=dept).count()
        
        overdue_allocations = Allocation.objects.filter(status='active', expected_return_date__lt=today, department=dept)
        upcoming_returns_count = Allocation.objects.filter(status='active', expected_return_date__gte=today, department=dept).count()
        
        recent_bookings = ResourceBooking.objects.filter(booked_by__department=dept).order_by('-created_at')[:5]
        recent_maintenance = MaintenanceRequest.objects.filter(asset__department=dept).order_by('-created_at')[:5]
        
    else:
        # Regular Employee view
        assets_available = Asset.objects.filter(status='available').count()
        assets_allocated = Asset.objects.filter(status='allocated', allocations__assignee=user, allocations__status='active').count()
        maintenance_today = MaintenanceRequest.objects.filter(status__in=['approved', 'technician_assigned', 'in_progress'], raised_by=user).count()
        active_bookings = ResourceBooking.objects.filter(status__in=['upcoming', 'ongoing'], booked_by=user).count()
        pending_transfers = TransferRequest.objects.filter(status='pending', requested_by=user).count()
        
        overdue_allocations = Allocation.objects.filter(status='active', expected_return_date__lt=today, assignee=user)
        upcoming_returns_count = Allocation.objects.filter(status='active', expected_return_date__gte=today, assignee=user).count()
        
        recent_bookings = ResourceBooking.objects.filter(booked_by=user).order_by('-created_at')[:5]
        recent_maintenance = MaintenanceRequest.objects.filter(raised_by=user).order_by('-created_at')[:5]

    # Specific tables for the user
    my_allocations = Allocation.objects.filter(status='active', assignee=user)
    my_bookings = ResourceBooking.objects.filter(status__in=['upcoming', 'ongoing'], booked_by=user)
    my_maintenance = MaintenanceRequest.objects.filter(raised_by=user)

    # Dynamic notifications
    user_notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
    
    # Recent logs for admin/managers
    recent_logs = []
    if user.role in ['admin', 'asset_manager']:
        recent_logs = ActionLog.objects.all().order_by('-timestamp')[:8]

    context = {
        'assets_available': assets_available,
        'assets_allocated': assets_allocated,
        'maintenance_today': maintenance_today,
        'active_bookings': active_bookings,
        'pending_transfers': pending_transfers,
        'overdue_allocations': overdue_allocations,
        'upcoming_returns_count': upcoming_returns_count,
        'my_allocations': my_allocations,
        'my_bookings': my_bookings,
        'my_maintenance': my_maintenance,
        'recent_bookings': recent_bookings,
        'recent_maintenance': recent_maintenance,
        'user_notifications': user_notifications,
        'recent_logs': recent_logs,
        'today': today,
    }
    return render(request, 'dashboard.html', context)
