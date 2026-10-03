from django import forms
from services.models import Category, Service, ServicePackage, ServiceFAQ, ServiceRequirement, ServiceGroup
from services.choices import RequirementFieldType
import json


class ServiceGroupForm(forms.ModelForm):
    class Meta:
        model = ServiceGroup
        fields = [
            "name",
            "slug",
            "short_description",
            "description",
            "icon_class",
            "cover_image",
            "theme_color",
            "display_order",
            "is_featured",
            "is_active",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Group Name"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "auto-generated-if-blank"}),
            "short_description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Short summary"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "icon_class": forms.TextInput(attrs={"class": "form-control", "placeholder": "bi-grid"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "theme_color": forms.TextInput(attrs={"class": "form-control", "placeholder": "#2563EB"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "seo_title": forms.TextInput(attrs={"class": "form-control"}),
            "seo_description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            "service_group",
            "name",
            "slug",
            "short_description",
            "description",
            "cover_image",
            "bootstrap_icon",
            "theme_color",
            "display_order",
            "is_featured",
            "is_active",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "service_group": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "auto-generated-if-blank"}),
            "short_description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Short summary"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Detailed description..."}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "bootstrap_icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "bi-grid"}),
            "theme_color": forms.TextInput(attrs={"class": "form-control", "placeholder": "#2563EB"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "seo_title": forms.TextInput(attrs={"class": "form-control"}),
            "seo_description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "category",
            "name",
            "slug",
            "short_description",
            "description",
            "cover_image",
            "icon_class",
            "starting_price",
            "estimated_duration",
            "theme_color",
            "display_order",
            "is_featured",
            "is_active",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Service Name"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "auto-generated-if-blank"}),
            "short_description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Short summary"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Detailed description..."}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "icon_class": forms.TextInput(attrs={"class": "form-control", "placeholder": "bi-tools"}),
            "starting_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "estimated_duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "2 hours"}),
            "theme_color": forms.TextInput(attrs={"class": "form-control", "placeholder": "#2563EB"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "seo_title": forms.TextInput(attrs={"class": "form-control"}),
            "seo_description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ServicePackageForm(forms.ModelForm):
    class Meta:
        model = ServicePackage
        fields = [
            "name",
            "slug",
            "short_description",
            "description",
            "price",
            "duration",
            "sort_order",
            "is_popular",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Package Name"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "auto-generated-if-blank"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 02:00:00"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_popular": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ServiceFAQForm(forms.ModelForm):
    class Meta:
        model = ServiceFAQ
        fields = [
            "question",
            "answer",
            "sort_order",
            "is_active",
        ]
        widgets = {
            "question": forms.TextInput(attrs={"class": "form-control"}),
            "answer": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ServiceRequirementForm(forms.ModelForm):
    choices_raw = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": 'Enter choices as a JSON list, e.g. ["Light", "Medium", "Heavy"]'}),
        label="Choices (for select, radio, checkbox)"
    )

    class Meta:
        model = ServiceRequirement
        fields = [
            "label",
            "field_name",
            "field_type",
            "placeholder",
            "help_text",
            "default_value",
            "required",
            "sort_order",
            "is_active",
        ]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "field_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. grease_level"}),
            "field_type": forms.Select(attrs={"class": "form-select"}),
            "placeholder": forms.TextInput(attrs={"class": "form-control"}),
            "help_text": forms.TextInput(attrs={"class": "form-control"}),
            "default_value": forms.TextInput(attrs={"class": "form-control"}),
            "required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["choices_raw"].initial = json.dumps(self.instance.choices)

    def clean_choices_raw(self):
        raw = self.cleaned_data.get("choices_raw")
        if not raw:
            return []
        try:
            val = json.loads(raw)
            if not isinstance(val, list):
                raise forms.ValidationError("Choices must be a JSON array (list).")
            return val
        except Exception:
            raise forms.ValidationError("Invalid JSON list format. Must be like: [\"Light\", \"Medium\"]")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.choices = self.cleaned_data.get("choices_raw") or []
        if commit:
            instance.save()
        return instance
