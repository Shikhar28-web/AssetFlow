from django.db import models
from django.conf import settings

class MaintenanceRequest(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('technician_assigned', 'Technician Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='maintenance_requests')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='raised_maintenance')
    description = models.TextField()
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='medium')
    photo = models.ImageField(upload_to='maintenance/photos/', null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Maint-{self.id} for {self.asset} ({self.get_status_display()})"
