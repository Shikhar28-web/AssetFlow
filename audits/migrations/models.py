from django.db import models
from django.conf import settings

class AuditCycle(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=100)
    department = models.ForeignKey('organization.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_cycles')
    location = models.CharField(max_length=100, blank=True, help_text="Filter assets by location")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    auditors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='assigned_audits')

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class AuditItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('missing', 'Missing'),
        ('damaged', 'Damaged'),
    ]

    audit_cycle = models.ForeignKey(AuditCycle, on_delete=models.CASCADE, related_name='items')
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='audit_items')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_audit_items')

    def __str__(self):
        return f"{self.asset} in {self.audit_cycle.name} - {self.get_status_display()}"
