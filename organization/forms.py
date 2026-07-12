import json
from django import forms
from .models import Department, AssetCategory
from accounts.models import User

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'head', 'parent_department', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code (e.g. ENG, HR)'}),
            'head': forms.Select(attrs={'class': 'form-control'}),
            'parent_department': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit Head choices to active users
        self.fields['head'].queryset = User.objects.filter(status='active')
        self.fields['head'].required = False
        self.fields['parent_department'].required = False
        if self.instance.pk:
            self.fields['parent_department'].queryset = Department.objects.exclude(pk=self.instance.pk)

class AssetCategoryForm(forms.ModelForm):
    schema_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'e.g. [\n  {"name": "Warranty Period (months)", "type": "number"},\n  {"name": "Brand", "type": "text"}\n]'}),
        label='Custom Fields Schema (JSON Array)',
        help_text='A JSON list of dicts with "name" and "type" keys. Supported types: text, number, date.'
    )

    class Meta:
        model = AssetCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Category Description'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fields_schema:
            self.initial['schema_text'] = json.dumps(self.instance.fields_schema, indent=2)

    def clean_schema_text(self):
        data = self.cleaned_data.get('schema_text')
        if not data or data.strip() == '':
            return []
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, list):
                raise forms.ValidationError("Schema must be a JSON list/array.")
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    raise forms.ValidationError(f"Item {idx} is not a valid object.")
                if 'name' not in item or 'type' not in item:
                    raise forms.ValidationError(f"Item {idx} must contain both 'name' and 'type' keys.")
                if item['type'] not in ['text', 'number', 'date', 'select']:
                    raise forms.ValidationError(f"Item {idx} type '{item['type']}' is invalid. Use 'text', 'number', 'date', or 'select'.")
            return parsed
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {str(e)}")

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Store clean schema array directly into fields_schema
        instance.fields_schema = self.cleaned_data.get('schema_text', [])
        if commit:
            instance.save()
        return instance
class RolePromotionForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role', 'department', 'status']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
