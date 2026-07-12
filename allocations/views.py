from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Allocation, TransferRequest
from .forms import AllocationForm, AssetReturnForm
from assets.models import Asset
from accounts.models import User
from notifications.models import Notification, ActionLog

def is_manager_or_admin(user):
    return user.is_authenticated and (user.role in ['admin', 'asset_manager'] or user.is_staff)

@login_required
@user_passes_test(is_manager_or_admin)
def allocate_asset(request, asset_pk=None):
    asset = None
    if asset_pk:
        asset = get_object_or_404(Asset, pk=asset_pk)
        if asset.status != 'available':
            current = Allocation.objects.filter(asset=asset, status='active').first()
            holder = "someone"
            if current:
                if current.assignee:
                    holder = current.assignee.get_full_name() or current.assignee.email
                elif current.department:
                    holder = f"Department {current.department.name}"
            messages.error(request, f"Asset '{asset.name}' is already allocated to {holder}. You can request a transfer instead.")
            return redirect('asset_detail', pk=asset.pk)

    if request.method == 'POST':
        form = AllocationForm(request.POST)
        if form.is_valid():
            target_asset = form.cleaned_data['asset']
            assignee = form.cleaned_data['assignee']
            department = form.cleaned_data['department']
            expected_return_date = form.cleaned_data['expected_return_date']

            try:
                with transaction.atomic():
                    # Thread-safe database lock on the Asset record
                    locked_asset = Asset.objects.select_for_update().get(pk=target_asset.pk)
                    if locked_asset.status != 'available':
                        raise ValueError(f"Asset is not available for allocation.")
                    
                    locked_asset.status = 'allocated'
                    locked_asset.department = assignee.department if assignee else department
                    locked_asset.save()

                    allocation = Allocation.objects.create(
                        asset=locked_asset,
                        assignee=assignee,
                        department=department,
                        allocated_by=request.user,
                        expected_return_date=expected_return_date,
                        status='active'
                    )

                    # Log the Action
                    holder_label = assignee.email if assignee else f"Dept: {department.name}"
                    ActionLog.objects.create(
                        user=request.user,
                        action="Asset Allocated",
                        details=f"Allocated {locked_asset.asset_tag} to {holder_label}. Expected return: {expected_return_date}"
                    )

                    # Create Notification
                    if assignee:
                        Notification.objects.create(
                            user=assignee,
                            message=f"Asset '{locked_asset.name}' [{locked_asset.asset_tag}] has been allocated to you. Expected return date: {expected_return_date or 'Indefinite'}"
                        )
                    
                    messages.success(request, f"Asset '{locked_asset.name}' allocated successfully.")
                    return redirect('asset_detail', pk=locked_asset.pk)
            except Exception as e:
                messages.error(request, f"Allocation failed: {str(e)}")
    else:
        form = AllocationForm(initial={'asset': asset})

    return render(request, 'allocations/allocate_form.html', {'form': form, 'asset': asset})

@login_required
@user_passes_test(is_manager_or_admin)
def return_asset(request, allocation_pk):
    allocation = get_object_or_404(Allocation, pk=allocation_pk, status='active')
    asset = allocation.asset

    if request.method == 'POST':
        form = AssetReturnForm(request.POST, instance=allocation)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Thread-safe database lock
                    locked_asset = Asset.objects.select_for_update().get(pk=asset.pk)
                    
                    # Update Allocation status
                    returned_alloc = form.save(commit=False)
                    returned_alloc.status = 'returned'
                    returned_alloc.returned_at = timezone.now()
                    returned_alloc.save()

                    # Revert Asset status back to available
                    locked_asset.status = 'available'
                    locked_asset.condition = form.cleaned_data['return_condition']
                    locked_asset.save()

                    # Log the Action
                    ActionLog.objects.create(
                        user=request.user,
                        action="Asset Returned",
                        details=f"Asset {locked_asset.asset_tag} returned by user. Notes: {form.cleaned_data.get('return_notes')}"
                    )

                    # Create Notification if assignee exists
                    if returned_alloc.assignee:
                        Notification.objects.create(
                            user=returned_alloc.assignee,
                            message=f"Return of asset '{locked_asset.name}' [{locked_asset.asset_tag}] has been approved and marked as Available."
                        )

                    messages.success(request, f"Asset '{locked_asset.name}' returned successfully.")
                    return redirect('asset_detail', pk=locked_asset.pk)
            except Exception as e:
                messages.error(request, f"Return failed: {str(e)}")
    else:
        form = AssetReturnForm(initial={'return_condition': asset.condition})

    return render(request, 'allocations/return_form.html', {'form': form, 'allocation': allocation})

@login_required
def raise_transfer_request(request, asset_pk):
    asset = get_object_or_404(Asset, pk=asset_pk)
    
    # Verify the asset is currently allocated
    current_alloc = Allocation.objects.filter(asset=asset, status='active').first()
    if not current_alloc or not current_alloc.assignee:
        messages.error(request, "This asset is not currently allocated to an employee and cannot be transferred.")
        return redirect('asset_detail', pk=asset.pk)

    if current_alloc.assignee == request.user:
        messages.error(request, "You are already the current holder of this asset.")
        return redirect('asset_detail', pk=asset.pk)

    # Check if there is already an active transfer request for this asset
    existing = TransferRequest.objects.filter(asset=asset, status='pending').first()
    if existing:
        messages.warning(request, "A transfer request for this asset is already pending.")
        return redirect('asset_detail', pk=asset.pk)

    # Create transfer request
    with transaction.atomic():
        transfer = TransferRequest.objects.create(
            asset=asset,
            current_holder=current_alloc.assignee,
            target_holder=request.user,
            requested_by=request.user,
            status='pending'
        )

        ActionLog.objects.create(
            user=request.user,
            action="Transfer Requested",
            details=f"Requested transfer of {asset.asset_tag} from {current_alloc.assignee.email} to {request.user.email}"
        )

        # Notify current holder
        Notification.objects.create(
            user=current_alloc.assignee,
            message=f"User {request.user.email} has requested a transfer of asset '{asset.name}' [{asset.asset_tag}] currently held by you."
        )
        
        # Notify managers
        managers = User.objects.filter(role__in=['admin', 'asset_manager'])
        for m in managers:
            Notification.objects.create(
                user=m,
                message=f"Transfer request raised for asset '{asset.name}' [{asset.asset_tag}] from {current_alloc.assignee.email} to {request.user.email}."
            )

    messages.success(request, f"Transfer request for '{asset.name}' raised successfully. Pending approval.")
    return redirect('asset_detail', pk=asset.pk)

@login_required
def transfer_list(request):
    user = request.user
    
    # Filter transfer requests by role
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        # Managers see all transfer requests
        transfers = TransferRequest.objects.all().order_by('-requested_at')
    elif user.role == 'department_head' and user.department:
        # Dept heads see transfers where current or target holder is in their dept
        transfers = TransferRequest.objects.filter(
            Q(current_holder__department=user.department) | 
            Q(target_holder__department=user.department)
        ).order_by('-requested_at')
    else:
        # Employees see transfers they requested or are involved in
        transfers = TransferRequest.objects.filter(
            Q(current_holder=user) | 
            Q(target_holder=user) | 
            Q(requested_by=user)
        ).order_by('-requested_at')

    return render(request, 'allocations/transfer_list.html', {'transfers': transfers})

@login_required
def approve_transfer(request, transfer_pk):
    transfer = get_object_or_404(TransferRequest, pk=transfer_pk, status='pending')
    user = request.user

    # Gated check: Asset Manager / Admin OR Dept Head of the current holder
    is_allowed = False
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        is_allowed = True
    elif user.role == 'department_head' and user.department and transfer.current_holder.department == user.department:
        is_allowed = True

    if not is_allowed:
        messages.error(request, "You do not have permission to approve this transfer request.")
        return redirect('transfer_list')

    try:
        with transaction.atomic():
            asset = Asset.objects.select_for_update().get(pk=transfer.asset.pk)
            
            # 1. Close current holder's allocation
            current_alloc = Allocation.objects.select_for_update().filter(asset=asset, assignee=transfer.current_holder, status='active').first()
            if current_alloc:
                current_alloc.status = 'returned'
                current_alloc.returned_at = timezone.now()
                current_alloc.return_condition = asset.condition
                current_alloc.return_notes = f"Transferred to {transfer.target_holder.email} (Appr: {user.email})"
                current_alloc.save()

            # 2. Create new allocation for target holder
            new_alloc = Allocation.objects.create(
                asset=asset,
                assignee=transfer.target_holder,
                department=transfer.target_holder.department,
                allocated_by=user,
                expected_return_date=None, # can be updated later
                status='active'
            )

            # 3. Update asset's department context
            asset.department = transfer.target_holder.department
            asset.save()

            # 4. Mark TransferRequest as approved
            transfer.status = 'approved'
            transfer.approved_by = user
            transfer.approved_at = timezone.now()
            transfer.save()

            # Log action
            ActionLog.objects.create(
                user=user,
                action="Transfer Approved",
                details=f"Approved transfer of {asset.asset_tag} to {transfer.target_holder.email}"
            )

            # Notifications
            Notification.objects.create(
                user=transfer.current_holder,
                message=f"Transfer of asset '{asset.name}' [{asset.asset_tag}] has been approved. It is no longer allocated to you."
            )
            Notification.objects.create(
                user=transfer.target_holder,
                message=f"Transfer of asset '{asset.name}' [{asset.asset_tag}] has been approved. The asset is now allocated to you."
            )

            messages.success(request, f"Transfer request approved. Asset '{asset.name}' is now allocated to {transfer.target_holder.email}.")
    except Exception as e:
        messages.error(request, f"Approval failed: {str(e)}")

    return redirect('transfer_list')

@login_required
def reject_transfer(request, transfer_pk):
    transfer = get_object_or_404(TransferRequest, pk=transfer_pk, status='pending')
    user = request.user

    # Gated check: Asset Manager / Admin OR Dept Head of the current holder
    is_allowed = False
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        is_allowed = True
    elif user.role == 'department_head' and user.department and transfer.current_holder.department == user.department:
        is_allowed = True

    if not is_allowed:
        messages.error(request, "You do not have permission to reject this transfer request.")
        return redirect('transfer_list')

    with transaction.atomic():
        transfer.status = 'rejected'
        transfer.approved_by = user
        transfer.approved_at = timezone.now()
        transfer.save()

        # Log action
        ActionLog.objects.create(
            user=user,
            action="Transfer Rejected",
            details=f"Rejected transfer of {transfer.asset.asset_tag} to {transfer.target_holder.email}"
        )

        # Notify requester
        Notification.objects.create(
            user=transfer.requested_by,
            message=f"Your transfer request for asset '{transfer.asset.name}' [{transfer.asset.asset_tag}] has been rejected."
        )

    messages.success(request, "Transfer request rejected.")
    return redirect('transfer_list')


from .models import DeviceRequest
from .forms import DeviceRequestForm

@login_required
def device_request_create(request):
    if request.method == 'POST':
        form = DeviceRequestForm(request.POST)
        if form.is_valid():
            device_request = form.save(commit=False)
            device_request.requested_by = request.user
            device_request.status = 'pending'
            device_request.save()

            # Create notification for admins/managers
            managers = User.objects.filter(role__in=['admin', 'asset_manager'])
            for m in managers:
                Notification.objects.create(
                    user=m,
                    message=f"New device request raised for category '{device_request.category.name}' by {request.user.email}."
                )

            # Create notification for department head if assignee has a department
            if request.user.department:
                heads = User.objects.filter(role='department_head', department=request.user.department)
                for h in heads:
                    Notification.objects.create(
                        user=h,
                        message=f"Department member {request.user.email} requested a device of category '{device_request.category.name}'."
                    )

            ActionLog.objects.create(
                user=request.user,
                action="Device Requested",
                details=f"Requested a device of category {device_request.category.name} with {device_request.priority} priority."
            )

            messages.success(request, f"Device request for '{device_request.category.name}' submitted successfully.")
            return redirect('device_request_list')
    else:
        form = DeviceRequestForm()
    return render(request, 'allocations/device_request_form.html', {'form': form})

@login_required
def device_request_list(request):
    requests = DeviceRequest.objects.filter(requested_by=request.user).order_by('-requested_at')
    return render(request, 'allocations/device_request_list.html', {'requests': requests})

@login_required
def device_request_manage(request):
    user = request.user
    # Gated check: Admin / Asset Manager / Department Head
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        requests = DeviceRequest.objects.all().order_by('-requested_at')
    elif user.role == 'department_head' and user.department:
        requests = DeviceRequest.objects.filter(requested_by__department=user.department).order_by('-requested_at')
    else:
        messages.error(request, "You do not have permission to access the device requests dashboard.")
        return redirect('dashboard')
    
    return render(request, 'allocations/device_request_manage.html', {'requests': requests})

@login_required
def device_request_approve(request, pk):
    device_request = get_object_or_404(DeviceRequest, pk=pk, status='pending')
    user = request.user
    
    # Gated check
    is_allowed = False
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        is_allowed = True
    elif user.role == 'department_head' and user.department and device_request.requested_by.department == user.department:
        is_allowed = True
        
    if not is_allowed:
        messages.error(request, "You do not have permission to approve this request.")
        return redirect('device_request_manage')

    # Query available assets of this category
    available_assets = Asset.objects.filter(category=device_request.category, status='available')

    if request.method == 'POST':
        asset_id = request.POST.get('asset')
        if not asset_id:
            messages.error(request, "Please select an asset to allocate.")
        else:
            asset = get_object_or_404(Asset, pk=asset_id, category=device_request.category, status='available')
            
            try:
                with transaction.atomic():
                    locked_asset = Asset.objects.select_for_update().get(pk=asset.pk)
                    if locked_asset.status != 'available':
                        raise ValueError("Asset is no longer available.")
                        
                    # Allocate asset
                    locked_asset.status = 'allocated'
                    locked_asset.department = device_request.requested_by.department
                    locked_asset.save()
                    
                    allocation = Allocation.objects.create(
                        asset=locked_asset,
                        assignee=device_request.requested_by,
                        department=device_request.requested_by.department,
                        allocated_by=request.user,
                        expected_return_date=None,
                        status='active'
                    )
                    
                    # Update device request status
                    device_request.status = 'approved'
                    device_request.processed_by = request.user
                    device_request.allocated_asset = locked_asset
                    device_request.processed_at = timezone.now()
                    device_request.save()
                    
                    # Action log
                    ActionLog.objects.create(
                        user=request.user,
                        action="Device Request Approved",
                        details=f"Approved device request #{device_request.id} for {device_request.requested_by.email} and allocated asset {locked_asset.asset_tag}."
                    )
                    
                    # Notify employee
                    Notification.objects.create(
                        user=device_request.requested_by,
                        message=f"Your request for a '{device_request.category.name}' has been approved! Asset '{locked_asset.name}' [{locked_asset.asset_tag}] is now allocated to you."
                    )
                    
                    messages.success(request, f"Request approved. Asset '{locked_asset.name}' allocated to {device_request.requested_by.email}.")
                    return redirect('device_request_manage')
            except Exception as e:
                messages.error(request, f"Approval failed: {str(e)}")
                
    return render(request, 'allocations/device_request_approve.html', {
        'request_item': device_request,
        'available_assets': available_assets
    })

@login_required
def device_request_reject(request, pk):
    device_request = get_object_or_404(DeviceRequest, pk=pk, status='pending')
    user = request.user
    
    # Gated check
    is_allowed = False
    if user.role in ['admin', 'asset_manager'] or user.is_staff:
        is_allowed = True
    elif user.role == 'department_head' and user.department and device_request.requested_by.department == user.department:
        is_allowed = True
        
    if not is_allowed:
        messages.error(request, "You do not have permission to reject this request.")
        return redirect('device_request_manage')
        
    with transaction.atomic():
        device_request.status = 'rejected'
        device_request.processed_by = request.user
        device_request.processed_at = timezone.now()
        device_request.save()
        
        ActionLog.objects.create(
            user=request.user,
            action="Device Request Rejected",
            details=f"Rejected device request #{device_request.id} for {device_request.requested_by.email}."
        )
        
        Notification.objects.create(
            user=device_request.requested_by,
            message=f"Your request for a '{device_request.category.name}' has been rejected."
        )
        
    messages.success(request, "Device request rejected successfully.")
    return redirect('device_request_manage')

