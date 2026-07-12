from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from .models import ResourceBooking
from .forms import ResourceBookingForm
from assets.models import Asset
from notifications.models import Notification, ActionLog

@login_required
def booking_list(request):
    bookings = ResourceBooking.objects.filter(booked_by=request.user).order_by('-start_time')
    
    # If the user is admin or manager, they see all bookings
    if request.user.role in ['admin', 'asset_manager'] or request.user.is_staff:
        all_bookings = ResourceBooking.objects.all().order_by('-start_time')
    else:
        # Dept heads see bookings in their department
        if request.user.role == 'department_head' and request.user.department:
            all_bookings = ResourceBooking.objects.filter(booked_by__department=request.user.department).order_by('-start_time')
        else:
            all_bookings = bookings

    bookable_assets = Asset.objects.filter(is_shared_bookable=True)
    
    # Auto-update status of bookings if they are ongoing or completed
    now = timezone.now()
    for booking in ResourceBooking.objects.filter(status='upcoming', start_time__lte=now):
        booking.status = 'ongoing'
        booking.save()
    for booking in ResourceBooking.objects.filter(status='ongoing', end_time__lte=now):
        booking.status = 'completed'
        booking.save()

    context = {
        'bookings': bookings,
        'all_bookings': all_bookings,
        'bookable_assets': bookable_assets,
    }
    return render(request, 'bookings/list.html', context)

@login_required
def book_resource(request, asset_pk=None):
    asset = None
    if asset_pk:
        asset = get_object_or_404(Asset, pk=asset_pk, is_shared_bookable=True)
        if asset.status != 'available':
            messages.error(request, f"Asset '{asset.name}' is currently {asset.get_status_display()} and cannot be booked.")
            return redirect('asset_detail', pk=asset.pk)

    if request.method == 'POST':
        form = ResourceBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Thread-safe database lock
                    target_asset = form.cleaned_data['asset']
                    locked_asset = Asset.objects.select_for_update().get(pk=target_asset.pk)
                    
                    booking = form.save(commit=False)
                    booking.booked_by = request.user
                    booking.status = 'upcoming'
                    booking.save()

                    # Create Action Log
                    ActionLog.objects.create(
                        user=request.user,
                        action="Resource Booked",
                        details=f"Booked {locked_asset.name} from {booking.start_time} to {booking.end_time}"
                    )

                    # Create Notification
                    Notification.objects.create(
                        user=request.user,
                        message=f"Your booking for '{locked_asset.name}' [{locked_asset.asset_tag}] has been confirmed for {booking.start_time.strftime('%Y-%m-%d %H:%M')} to {booking.end_time.strftime('%H:%M')}."
                    )

                    messages.success(request, f"Booking for '{locked_asset.name}' has been confirmed.")
                    return redirect('booking_list')
            except Exception as e:
                messages.error(request, f"Booking failed: {str(e)}")
    else:
        # Pre-select asset if pk is provided
        form = ResourceBookingForm(initial={'asset': asset})

    return render(request, 'bookings/book_form.html', {'form': form, 'asset': asset})

@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(ResourceBooking, pk=pk)
    
    # Gated check: owner of booking OR manager/admin
    is_allowed = (booking.booked_by == request.user) or (request.user.role in ['admin', 'asset_manager']) or request.user.is_staff
    if not is_allowed:
        messages.error(request, "You do not have permission to cancel this booking.")
        return redirect('booking_list')

    if booking.status in ['completed', 'cancelled']:
        messages.warning(request, f"Booking cannot be cancelled because it is already {booking.status}.")
        return redirect('booking_list')

    with transaction.atomic():
        booking.status = 'cancelled'
        booking.save()

        # Log action
        ActionLog.objects.create(
            user=request.user,
            action="Booking Cancelled",
            details=f"Cancelled booking for {booking.asset.name} (originally scheduled at {booking.start_time})"
        )

        # Notify user
        Notification.objects.create(
            user=booking.booked_by,
            message=f"Your booking for '{booking.asset.name}' [{booking.asset.asset_tag}] scheduled for {booking.start_time.strftime('%Y-%m-%d %H:%M')} has been cancelled."
        )

    messages.success(request, "Booking cancelled successfully.")
    return redirect('booking_list')

@login_required
def booking_calendar_api(request, asset_pk):
    # API view that returns booking slots as JSON for FullCalendar.js
    asset = get_object_or_404(Asset, pk=asset_pk, is_shared_bookable=True)
    bookings = ResourceBooking.objects.filter(asset=asset, status__in=['upcoming', 'ongoing', 'completed'])
    
    events = []
    for b in bookings:
        color = '#5f3dc4' # default violet
        if b.status == 'ongoing':
            color = '#37b24d' # green
        elif b.status == 'completed':
            color = '#868e96' # grey
            
        events.append({
            'id': b.id,
            'title': f"Booked by {b.booked_by.email}",
            'start': b.start_time.isoformat(),
            'end': b.end_time.isoformat(),
            'color': color,
            'allDay': False
        })
        
    return JsonResponse(events, safe=False)
