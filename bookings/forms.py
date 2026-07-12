from django import forms
from django.utils import timezone
from .models import ResourceBooking
from assets.models import Asset

class ResourceBookingForm(forms.ModelForm):
    class Meta:
        model = ResourceBooking
        fields = ['asset', 'start_time', 'end_time']
        widgets = {
            'asset': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit to assets marked as bookable
        self.fields['asset'].queryset = Asset.objects.filter(is_shared_bookable=True, status='available')

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise forms.ValidationError("Booking start time cannot be in the past.")
        return start_time

    def clean(self):
        cleaned_data = super().clean()
        asset = cleaned_data.get('asset')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("End time must be after start time.")

            # Overlap check
            # We filter for upcoming/ongoing bookings that overlap
            # Two bookings overlap if booking1.start < booking2.end AND booking1.end > booking2.start
            overlapping = ResourceBooking.objects.filter(
                asset=asset,
                status__in=['upcoming', 'ongoing'],
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            # Exclude current instance if editing
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                first_overlap = overlapping.first()
                start_str = first_overlap.start_time.strftime('%Y-%m-%d %H:%M')
                end_str = first_overlap.end_time.strftime('%Y-%m-%d %H:%M')
                raise forms.ValidationError(
                    f"This time slot overlaps with an existing booking by {first_overlap.booked_by.email} ({start_str} to {end_str})."
                )

        return cleaned_data
