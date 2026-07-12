from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import MaintenanceRequest
from .forms import MaintenanceRequestForm, MaintenanceUpdateForm
from assets.models import Asset
from notifications.models import ActionLog

def is_manager_or_admin(user):
    return user.is_authenticated and (user.role in ['admin', 'asset_manager'] or user.is_staff)

@login_required
def maintenance_list(request):
    user = request.user
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        requests = MaintenanceRequest.objects.all().order_by('-created_at')
    elif user.role == 'department_head' and user.department:
        requests = MaintenanceRequest.objects.filter(asset__department=user.department).order_by('-created_at')
    else:
        requests = MaintenanceRequest.objects.filter(raised_by=user).order_by('-created_at')

    return render(request, 'maintenance/list.html', {'requests': requests})

@login_required
def raise_maintenance(request, asset_pk=None):
    asset = None
    if asset_pk:
        asset = get_object_or_404(Asset, pk=asset_pk)

    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            req = form.save(commit=False)
            req.raised_by = request.user
            req.status = 'pending'
            req.save()

            ActionLog.objects.create(
                user=request.user,
                action="Maintenance Raised",
                details=f"Raised maintenance request {req.id} for {req.asset.name} [{req.asset.asset_tag}]"
            )

            messages.success(request, f"Maintenance request for '{req.asset.name}' has been raised successfully.")
            return redirect('maintenance_list')
    else:
        form = MaintenanceRequestForm(initial={'asset': asset}, user=request.user)

    return render(request, 'maintenance/raise_form.html', {'form': form, 'asset': asset})

@login_required
def maintenance_detail(request, pk):
    req = get_object_or_404(MaintenanceRequest, pk=pk)
    user = request.user
    
    # Check view permission: owner, department head of asset, or manager
    is_allowed = False
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        is_allowed = True
    elif user.role == 'department_head' and user.department and req.asset.department == user.department:
        is_allowed = True
    elif req.raised_by == user:
        is_allowed = True

    if not is_allowed:
        messages.error(request, "You do not have permission to view this maintenance request.")
        return redirect('maintenance_list')

    if request.method == 'POST' and is_manager_or_admin(user):
        form = MaintenanceUpdateForm(request.POST, instance=req)
        if form.is_valid():
            with transaction.atomic():
                updated_req = form.save(commit=False)
                if updated_req.status == 'resolved':
                    updated_req.resolved_at = timezone.now()
                updated_req.save()

                ActionLog.objects.create(
                    user=user,
                    action="Maintenance Updated",
                    details=f"Updated maintenance request {req.id} status to '{updated_req.get_status_display()}'"
                )

            messages.success(request, "Maintenance request updated successfully.")
            return redirect('maintenance_detail', pk=req.pk)
    else:
        form = MaintenanceUpdateForm(instance=req)

    return render(request, 'maintenance/detail.html', {'request_obj': req, 'form': form})
