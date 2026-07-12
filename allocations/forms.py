from django import forms
from .models import Allocation, TransferRequest
from assets.models import Asset
from accounts.models import User
from organization.models import Department

class AllocationForm(forms.ModelForm):
    class Meta:
        model = Allocation
        fields = ['asset', 'assignee', 'department', 'expected_return_date']
        widgets = {
            'asset': forms.Select(attrs={'class': 'form-control'}),
            'assignee': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'expected_return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit assets to available ones, unless we are editing an existing allocation
        if not self.instance.pk:
            self.fields['asset'].queryset = Asset.objects.filter(status='available')
        
        self.fields['assignee'].queryset = User.objects.filter(status='active')
        self.fields['assignee'].required = False
        self.fields['department'].queryset = Department.objects.filter(status='active')
        self.fields['department'].required = False
        self.fields['expected_return_date'].required = False

    def clean(self):
        cleaned_data = super().clean()
        assignee = cleaned_data.get('assignee')
        department = cleaned_data.get('department')
        asset = cleaned_data.get('asset')

        if not assignee and not department:
            raise forms.ValidationError("You must specify either an Assignee Employee or an Assignee Department.")

        # Check if asset is available
        if asset and not self.instance.pk:
            if asset.status != 'available':
                current = Allocation.objects.filter(asset=asset, status='active').first()
                holder = "Unknown"
                if current:
                    if current.assignee:
                        holder = current.assignee.get_full_name() or current.assignee.email
                    elif current.department:
                        holder = f"Department {current.department.name}"
                raise forms.ValidationError(
                    f"Asset is currently held by {holder} and cannot be allocated."
                )

        return cleaned_data

class AssetReturnForm(forms.ModelForm):
    class Meta:
        model = Allocation
        fields = ['return_condition', 'return_notes']
        widgets = {
            'return_condition': forms.Select(choices=Asset.CONDITION_CHOICES, attrs={'class': 'form-control'}),
            'return_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional check-in notes...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['return_condition'].required = True
        self.fields['return_notes'].required = False
