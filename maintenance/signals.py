from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MaintenanceRequest
from notifications.models import Notification, ActionLog

@receiver(post_save, sender=MaintenanceRequest)
def handle_maintenance_status_change(sender, instance, created, **kwargs):
    asset = instance.asset
    
    if instance.status in ['approved', 'technician_assigned', 'in_progress']:
        if asset.status != 'under_maintenance':
            asset.status = 'under_maintenance'
            asset.save()
            
            # Notify requester
            Notification.objects.create(
                user=instance.raised_by,
                message=f"Maintenance request for asset '{asset.name}' [{asset.asset_tag}] has been approved. The asset is now Under Maintenance."
            )
    elif instance.status == 'resolved':
        if asset.status != 'available':
            asset.status = 'available'
            asset.save()
            
            # Notify requester
            Notification.objects.create(
                user=instance.raised_by,
                message=f"Maintenance request for asset '{asset.name}' [{asset.asset_tag}] has been resolved. The asset is now Available."
            )
    elif instance.status == 'rejected':
        Notification.objects.create(
            user=instance.raised_by,
            message=f"Maintenance request for asset '{asset.name}' [{asset.asset_tag}] has been rejected."
        )
