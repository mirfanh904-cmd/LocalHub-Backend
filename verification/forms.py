from django import forms

from .models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
)


class VerificationSubmissionForm(forms.ModelForm):
    class Meta:
        model = ProfessionalVerification
        fields = []


class VerificationDocumentForm(forms.ModelForm):
    class Meta:
        model = ProfessionalVerificationDocument
        fields = [
            "document_type",
            "document_number",
            "document_file",
        ]

        widgets = {
            "document_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "document_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "document_file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }


class VerificationReviewForm(forms.ModelForm):
    class Meta:
        model = ProfessionalVerification

        fields = [
            "status",
            "rejection_reason",
            "expires_at",
        ]

        widgets = {
            "status": forms.Select(
                attrs={"class": "form-select"}
            ),
            "rejection_reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "expires_at": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
        }