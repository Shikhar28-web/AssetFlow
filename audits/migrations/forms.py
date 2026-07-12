from django import forms
from .models import AuditCycle, AuditItem
from organization.models import Department
from accounts.models import User

class AuditCycleForm(forms.ModelForm):
    class Meta:
        model = AuditCycle
        fields = ['name', 'department', 'location', 'start_date', 'end_date', 'auditors']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q3 Electronics Audit'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Floor 2 (Optional)'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'auditors': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].required = False
        self.fields['location'].required = False
        self.fields['auditors'].queryset = User.objects.filter(status='active')
