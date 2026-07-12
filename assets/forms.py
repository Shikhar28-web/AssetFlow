from django import forms
from .models import Asset
from organization.models import AssetCategory

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['name', 'category', 'serial_number', 'acquisition_date', 'acquisition_cost', 'condition', 'location', 'photo', 'is_shared_bookable', 'status', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asset Name'}),
            'category': forms.Select(attrs={'class': 'form-control', 'onchange': 'this.form.setAttribute("novalidate", "novalidate"); this.form.submit();'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number'}),
            'acquisition_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'acquisition_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Acquisition Cost'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current Location'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'is_shared_bookable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo'].required = False
        self.fields['department'].required = False
        self.fields['location'].required = False
        self.fields['serial_number'].required = False
        self.fields['condition'].required = False
        
        # Check for category and build dynamic fields
        category = None
        if self.instance and self.instance.pk and self.instance.category:
            category = self.instance.category
        elif self.data and self.data.get('category'):
            try:
                category = AssetCategory.objects.get(pk=self.data.get('category'))
            except AssetCategory.DoesNotExist:
                pass

        if category and category.fields_schema:
            for field in category.fields_schema:
                name = field.get('name')
                field_type = field.get('type')
                field_key = f"custom_{name.lower().replace(' ', '_')}"
                
                # Check for initial value in custom_attributes dict
                initial_val = None
                if self.instance and self.instance.pk and isinstance(self.instance.custom_attributes, dict):
                    initial_val = self.instance.custom_attributes.get(name)

                # Generate matching django form field
                if field_type == 'number':
                    self.fields[field_key] = forms.IntegerField(
                        label=name,
                        required=False,
                        initial=initial_val,
                        widget=forms.NumberInput(attrs={'class': 'form-control'})
                    )
                elif field_type == 'date':
                    self.fields[field_key] = forms.DateField(
                        label=name,
                        required=False,
                        initial=initial_val,
                        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                    )
                else:
                    self.fields[field_key] = forms.CharField(
                        label=name,
                        required=False,
                        initial=initial_val,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Collect custom fields back into json dict
        custom_attrs = {}
        if instance.category and instance.category.fields_schema:
            for field in instance.category.fields_schema:
                name = field.get('name')
                field_key = f"custom_{name.lower().replace(' ', '_')}"
                if field_key in self.cleaned_data:
                    val = self.cleaned_data[field_key]
                    if val is not None:
                        # Convert date object to string to keep JSON serializable
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        custom_attrs[name] = val
                        
        instance.custom_attributes = custom_attrs
        if commit:
            instance.save()
        return instance
