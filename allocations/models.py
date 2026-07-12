from django.db import models
from django.conf import settings

class Allocation(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
    ]

    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='allocations')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='allocations')
    department = models.ForeignKey('organization.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='allocations')
    allocated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_allocations')
    allocated_at = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(max_length=20, null=True, blank=True)
    return_notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        holder = self.assignee.get_full_name() or self.assignee.email if self.assignee else (self.department.name if self.department else 'Unknown')
        return f"{self.asset} allocated to {holder} ({self.get_status_display()})"

class TransferRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='transfer_requests')
    current_holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfers_from')
    target_holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfers_to')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfers_requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_approved')
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transfer {self.asset} from {self.current_holder} to {self.target_holder} ({self.get_status_display()})"

class DeviceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_requests')
    category = models.ForeignKey('organization.AssetCategory', on_delete=models.CASCADE, related_name='device_requests')
    purpose = models.TextField()
    priority = models.CharField(max_length=15, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Track approval/allocation
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_device_requests')
    allocated_asset = models.ForeignKey('assets.Asset', on_delete=models.SET_NULL, null=True, blank=True, related_name='device_allocations')
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request for {self.category.name} by {self.requested_by.email} ({self.get_status_display()})"

