from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, Address, ProfessionalProfile
from django.contrib.auth.forms import PasswordChangeForm


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First Name"
            }
        )
    )

    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last Name"
            }
        )
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email Address"
            }
        )
    )

    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Phone Number"
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password"
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm Password"
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Email already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:

            if password != confirm_password:
                self.add_error(
                    "confirm_password",
                    "Passwords do not match."
                )

            validate_password(password)

        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control",
                   "placeholder": "Enter your email"}))

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password"}))

    remember_me = forms.BooleanField(
        required=False)


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100, required=False)
    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "profile_picture",
            "date_of_birth",
            "gender",
            "occupation",
            "bio",
            "city",
            "state",
            "country",
            "preferred_language",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "bio": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")

        super().__init__(*args, **kwargs)

        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["gender"].widget.attrs["class"] = "form-select"
        self.fields["country"].widget.attrs["class"] = "form-select"
        self.fields["preferred_language"].widget.attrs["class"] = "form-select"
        self.fields["profile_picture"].widget.attrs["class"] = "form-control"


class AddressForm(forms.ModelForm):

    class Meta:

        model = Address

        fields = [

            "full_name",
            "phone",
            "address_type",
            "house_name",
            "area",
            "landmark",
            "city",
            "state",
            "country",
            "postal_code",

        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["address_type"].widget.attrs["class"] = "form-select"

        self.fields["country"].widget.attrs["class"] = "form-select"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        if (
                self.user
                and not self.instance.pk
                and Address.objects.filter(
            user=self.user,
            is_active=True,
        ).count() >= 5
        ):
            raise ValidationError(
                "You can save a maximum of 5 addresses."
            )

        return cleaned_data

# password change
class LocalHubPasswordChangeForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "old_password": "Current Password",
            "new_password1": "New Password",
            "new_password2": "Confirm New Password",
        }

        for name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "form-control",
                "placeholder": placeholders[name],
            })

class ProfessionalProfileForm(forms.ModelForm):
    class Meta:
        model = ProfessionalProfile
        fields = [
            "professional_title",
            "bio",
            "experience_years",
            "hourly_rate",
            "minimum_charge",
            "working_radius",
            "skills",
            "languages",
            "availability_status",

        ]
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 5,
                }
            ),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            for field_name in [
                "professional_title",
                "bio",
                "experience_years",
                "hourly_rate",
                "minimum_charge",
                "working_radius",
            ]:
                self.fields[field_name].widget.attrs["class"] = "form-control"

            self.fields["availability_status"].widget.attrs["class"] = "form-select"

            self.fields["skills"].widget = forms.CheckboxSelectMultiple()

            self.fields["languages"].widget = forms.CheckboxSelectMultiple()