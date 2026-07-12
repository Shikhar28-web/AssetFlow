from django import forms
from .models import MaintenanceRequest
from assets.models import Asset
from accounts.models import User

class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['asset', 'description', 'priority', 'photo']
        widgets = {
            'asset': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the issue...'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If user is provided, limit assets to those allocated to them, OR list all available/allocated assets
        if user and user.role not in ['admin', 'asset_manager']:
            # Regular employee can raise maintenance for assets allocated to them
            self.fields['asset'].queryset = Asset.objects.filter(allocations__assignee=user, allocations__status='active')
        else:
            self.fields['asset'].queryset = Asset.objects.all()

class MaintenanceUpdateForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['status', 'assigned_technician', 'resolution_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_technician': forms.Select(attrs={'class': 'form-control'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide details on how the issue was resolved...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Technicians can be any employee or admin, list active users
        self.fields['assigned_technician'].queryset = User.objects.filter(status='active')
        self.fields['assigned_technician'].required = False
        self.fields['resolution_notes'].required = False
