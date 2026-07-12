from django.db import models
from django.conf import settings

class Asset(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('allocated', 'Allocated'),
        ('reserved', 'Reserved'),
        ('under_maintenance', 'Under Maintenance'),
        ('lost', 'Lost'),
        ('retired', 'Retired'),
        ('disposed', 'Disposed'),
    ]

    name = models.CharField(max_length=100)
    category = models.ForeignKey('organization.AssetCategory', on_delete=models.PROTECT, related_name='assets')
    asset_tag = models.CharField(max_length=20, unique=True, blank=True)
    serial_number = models.CharField(max_length=50, blank=True)
    acquisition_date = models.DateField()
    acquisition_cost = models.DecimalField(max_digits=12, decimal_places=2)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    location = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='assets/photos/', null=True, blank=True)
    is_shared_bookable = models.BooleanField(default=False, verbose_name="Shared / Bookable")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    department = models.ForeignKey('organization.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    custom_attributes = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            # Run inside atomic block or simple max-index check
            # Find the highest ID and build a unique tag
            last_asset = Asset.objects.all().order_by('id').last()
            next_id = (last_asset.id + 1) if last_asset else 1
            self.asset_tag = f"AF-{next_id:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} [{self.asset_tag}]"
