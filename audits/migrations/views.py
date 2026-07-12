from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import AuditCycle, AuditItem
from .forms import AuditCycleForm
from assets.models import Asset
from notifications.models import Notification, ActionLog

def is_manager_or_admin(user):
    return user.is_authenticated and (user.role in ['admin', 'asset_manager'] or user.is_staff)

@login_required
def audit_list(request):
    user = request.user
    
    # Managers see all cycles
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        cycles = AuditCycle.objects.all().order_by('-created_at')
    else:
        # Auditors see cycles they are assigned to
        cycles = AuditCycle.objects.filter(auditors=user).order_by('-created_at')

    return render(request, 'audits/list.html', {'cycles': cycles})

@login_required
@user_passes_test(is_manager_or_admin)
def audit_create(request):
    if request.method == 'POST':
        form = AuditCycleForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    cycle = form.save()
                    
                    # Identify scope assets
                    assets = Asset.objects.exclude(status__in=['retired', 'disposed'])
                    if cycle.department:
                        assets = assets.filter(department=cycle.department)
                    if cycle.location:
                        assets = assets.filter(location__icontains=cycle.location)

                    # Create AuditItems
                    items = []
                    for asset in assets:
                        items.append(AuditItem(
                            audit_cycle=cycle,
                            asset=asset,
                            status='pending'
                        ))
                    
                    if items:
                        AuditItem.objects.bulk_create(items)
                        
                    ActionLog.objects.create(
                        user=request.user,
                        action="Audit Cycle Created",
                        details=f"Created audit '{cycle.name}' with {len(items)} items in scope"
                    )

                    # Notify auditors
                    for auditor in cycle.auditors.all():
                        Notification.objects.create(
                            user=auditor,
                            message=f"You have been assigned as an auditor for the audit cycle '{cycle.name}'."
                        )

                    messages.success(request, f"Audit cycle '{cycle.name}' has been created with {len(items)} assets in scope.")
                    return redirect('audit_list')
            except Exception as e:
                messages.error(request, f"Failed to create audit cycle: {str(e)}")
    else:
        form = AuditCycleForm()

    return render(request, 'audits/form.html', {'form': form, 'title': 'Create Audit Cycle'})

@login_required
def audit_detail(request, pk):
    cycle = get_object_or_404(AuditCycle, pk=pk)
    user = request.user
    
    # Check access permission: assigned auditor or manager
    is_allowed = (user.role in ['admin', 'asset_manager']) or user.is_staff or cycle.auditors.filter(pk=user.pk).exists()
    if not is_allowed:
        messages.error(request, "You do not have permission to access this audit cycle.")
        return redirect('audit_list')

    # Item filters
    status_filter = request.GET.get('status', '')
    items = cycle.items.all().order_by('asset__asset_tag')
    if status_filter:
        items = items.filter(status=status_filter)

    # Discrepancies (Missing or Damaged)
    discrepancy_items = cycle.items.filter(status__in=['missing', 'damaged'])

    # Calculation percentage
    total = cycle.items.count()
    completed = cycle.items.exclude(status='pending').count()
    percent_complete = int((completed / total) * 100) if total > 0 else 100

    context = {
        'cycle': cycle,
        'items': items,
        'discrepancy_items': discrepancy_items,
        'status_filter': status_filter,
        'percent_complete': percent_complete,
        'total': total,
        'completed': completed,
    }
    return render(request, 'audits/detail.html', context)

@login_required
def audit_item_verify(request, cycle_pk, item_pk):
    cycle = get_object_or_404(AuditCycle, pk=cycle_pk)
    item = get_object_or_404(AuditItem, pk=item_pk, audit_cycle=cycle)
    
    # Gated check: assigned auditor or manager
    user = request.user
    is_allowed = (user.role in ['admin', 'asset_manager']) or user.is_staff or cycle.auditors.filter(pk=user.pk).exists()
    if not is_allowed:
        messages.error(request, "You do not have permission to verify items in this audit cycle.")
        return redirect('audit_detail', pk=cycle.pk)

    if cycle.status == 'closed':
        messages.error(request, "This audit cycle has already been closed and locked.")
        return redirect('audit_detail', pk=cycle.pk)

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if status in ['verified', 'missing', 'damaged']:
            with transaction.atomic():
                item.status = status
                item.notes = notes
                item.verified_by = user
                item.verified_at = timezone.now()
                item.save()
                
                # If item is verified and asset is currently marked as lost, we can auto restore it or log
                ActionLog.objects.create(
                    user=user,
                    action="Audit Item Verified",
                    details=f"Verified {item.asset.asset_tag} in '{cycle.name}' as '{status.upper()}'"
                )
                
            messages.success(request, f"Asset {item.asset.asset_tag} verified successfully.")
        else:
            messages.error(request, "Invalid verification status selection.")

    return redirect('audit_detail', pk=cycle.pk)

@login_required
@user_passes_test(is_manager_or_admin)
def audit_close(request, pk):
    cycle = get_object_or_404(AuditCycle, pk=pk, status='active')
    
    # Check if there are pending items remaining
    pending_count = cycle.items.filter(status='pending').count()
    if pending_count > 0:
        messages.warning(request, f"Cannot close cycle. There are still {pending_count} pending assets that have not been verified.")
        return redirect('audit_detail', pk=cycle.pk)

    try:
        with transaction.atomic():
            # Lock assets and update statuses based on discrepancies
            missing_items = cycle.items.filter(status='missing')
            for item in missing_items:
                asset = Asset.objects.select_for_update().get(pk=item.asset.pk)
                asset.status = 'lost'
                asset.save()
                
                # Notify managers
                managers = User.objects.filter(role__in=['admin', 'asset_manager'])
                for m in managers:
                    Notification.objects.create(
                        user=m,
                        message=f"CRITICAL: Asset '{asset.name}' [{asset.asset_tag}] marked as LOST during audit '{cycle.name}'."
                    )

            damaged_items = cycle.items.filter(status='damaged')
            for item in damaged_items:
                asset = Asset.objects.select_for_update().get(pk=item.asset.pk)
                asset.condition = 'damaged'
                asset.save()
                
                # Suggest raising maintenance request
                managers = User.objects.filter(role__in=['admin', 'asset_manager'])
                for m in managers:
                    Notification.objects.create(
                        user=m,
                        message=f"WARNING: Asset '{asset.name}' [{asset.asset_tag}] marked as DAMAGED during audit '{cycle.name}'."
                    )

            # Close cycle
            cycle.status = 'closed'
            cycle.save()

            ActionLog.objects.create(
                user=request.user,
                action="Audit Cycle Closed",
                details=f"Closed audit cycle '{cycle.name}' and reconciled asset statuses."
            )

        messages.success(request, f"Audit cycle '{cycle.name}' closed successfully. Reconciliations complete.")
    except Exception as e:
        messages.error(request, f"Failed to close audit cycle: {str(e)}")

    return redirect('audit_detail', pk=cycle.pk)
