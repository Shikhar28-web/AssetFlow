import csv
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponse
from django.utils import timezone
from .models import Asset
from .forms import AssetForm
from organization.models import AssetCategory, Department
from notifications.models import ActionLog

def is_manager_or_admin(user):
    return user.is_authenticated and (user.role in ['admin', 'asset_manager'] or user.is_staff)

@login_required
def asset_list(request):
    assets = Asset.objects.all().order_by('-id')
    
    # Filtering query parameters
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status_choice = request.GET.get('status', '')
    location = request.GET.get('location', '')
    bookable = request.GET.get('bookable', '')
    
    if query:
        assets = assets.filter(
            Q(name__icontains=query) |
            Q(asset_tag__icontains=query) |
            Q(serial_number__icontains=query)
        )
    if category_id:
        assets = assets.filter(category_id=category_id)
    if status_choice:
        assets = assets.filter(status=status_choice)
    if location:
        assets = assets.filter(location__icontains=location)
    if bookable:
        assets = assets.filter(is_shared_bookable=(bookable == 'true'))

    categories = AssetCategory.objects.all().order_by('name')
    
    context = {
        'assets': assets,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'status_choice': status_choice,
        'location': location,
        'bookable': bookable,
        'status_list': Asset.STATUS_CHOICES,
    }
    return render(request, 'assets/list.html', context)

@login_required
@user_passes_test(is_manager_or_admin)
def asset_register(request):
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES)
        # Check if they just reloaded to change category
        if 'save_asset' in request.POST:
            if form.is_valid():
                asset = form.save()
                ActionLog.objects.create(
                    user=request.user,
                    action="Asset Registered",
                    details=f"Registered asset {asset.name} ({asset.asset_tag}) under category {asset.category.name}"
                )
                messages.success(request, f"Asset '{asset.name}' has been successfully registered with tag {asset.asset_tag}.")
                return redirect('asset_list')
        else:
            # Dropdown triggered reload - bypass normal form validation
            messages.info(request, "Updated custom attribute fields for the selected category.")
    else:
        form = AssetForm()

    return render(request, 'assets/form.html', {'form': form, 'title': 'Register Asset'})

@login_required
@user_passes_test(is_manager_or_admin)
def asset_edit(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES, instance=asset)
        if 'save_asset' in request.POST:
            if form.is_valid():
                form.save()
                ActionLog.objects.create(
                    user=request.user,
                    action="Asset Updated",
                    details=f"Updated asset {asset.name} ({asset.asset_tag})"
                )
                messages.success(request, f"Asset '{asset.name}' has been updated.")
                return redirect('asset_detail', pk=asset.pk)
        else:
            messages.info(request, "Updated custom attribute fields for the selected category.")
    else:
        form = AssetForm(instance=asset)

    return render(request, 'assets/form.html', {'form': form, 'title': f'Edit Asset: {asset.asset_tag}'})

@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    
    # Retrieve asset histories
    allocations = asset.allocations.all().order_by('-allocated_at')
    maintenance = asset.maintenance_requests.all().order_by('-created_at')
    bookings = asset.bookings.all().order_by('-start_time')
    
    context = {
        'asset': asset,
        'allocations': allocations,
        'maintenance': maintenance,
        'bookings': bookings,
    }
    return render(request, 'assets/detail.html', context)



@login_required
@user_passes_test(is_manager_or_admin)
def reports_view(request):
    # Check if CSV export is requested
    export_csv = request.GET.get('export', '')
    
    if export_csv == 'assets':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assetflow_assets_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Asset Tag', 'Name', 'Category', 'Status', 'Condition', 'Location', 'Acquisition Cost', 'Acquisition Date'])
        
        for asset in Asset.objects.all():
            writer.writerow([
                asset.asset_tag,
                asset.name,
                asset.category.name,
                asset.get_status_display(),
                asset.get_condition_display(),
                asset.location,
                asset.acquisition_cost,
                asset.acquisition_date
            ])
        return response

    # 1. General Utilization statistics
    total_assets = Asset.objects.exclude(status__in=['retired', 'disposed']).count()
    allocated_assets = Asset.objects.filter(status='allocated').count()
    utilization_rate = int((allocated_assets / total_assets) * 100) if total_assets > 0 else 0

    # 2. Maintenance frequency by Category
    maint_by_category = AssetCategory.objects.annotate(
        request_count=Count('assets__maintenance_requests')
    ).order_by('-request_count')

    # 3. Department allocation summaries
    dept_allocations = Department.objects.annotate(
        active_allocations=Count('allocations', filter=Q(allocations__status='active'))
    ).order_by('-active_allocations')

    # 4. Most booked assets (shared resources)
    most_booked = Asset.objects.filter(is_shared_bookable=True).annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:10]

    # 5. Assets nearing retirement (older than 4 years)
    four_years_ago = timezone.localdate() - datetime.timedelta(days=4*365)
    retirement_candidates = Asset.objects.filter(
        acquisition_date__lte=four_years_ago
    ).exclude(status__in=['retired', 'disposed']).order_by('acquisition_date')

    context = {
        'total_assets': total_assets,
        'allocated_assets': allocated_assets,
        'utilization_rate': utilization_rate,
        'maint_by_category': maint_by_category,
        'dept_allocations': dept_allocations,
        'most_booked': most_booked,
        'retirement_candidates': retirement_candidates,
    }
    return render(request, 'assets/reports.html', context)

