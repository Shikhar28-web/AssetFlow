from django.db import models
from django.conf import settings

class ResourceBooking(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='bookings')
    booked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset} booked by {self.booked_by} on {self.start_time.strftime('%Y-%m-%d %H:%M')}"
