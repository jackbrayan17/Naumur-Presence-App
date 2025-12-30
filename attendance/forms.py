from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Department, User


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False, label=_("Keep me signed in"), widget=forms.CheckboxInput()
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "input"})
        self.fields["password"].widget.attrs.update({"class": "input"})


class EmployeeCreateForm(forms.Form):
    full_name = forms.CharField(label=_("Full name"), max_length=150)
    username = forms.CharField(label=_("Username"), max_length=150)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    confirm_password = forms.CharField(
        label=_("Confirm password"), widget=forms.PasswordInput
    )
    department = forms.ModelChoiceField(label=_("Department"), queryset=Department.objects.none())
    start_date = forms.DateField(
        label=_("Start date"), initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("Username already exists."))
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", _("Passwords do not match."))
        return cleaned

    def save(self) -> User:
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            role=User.Roles.EMPLOYEE,
            first_name=first_name,
            last_name=last_name,
            department=self.cleaned_data["department"],
            start_date=self.cleaned_data["start_date"],
        )
        return user

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.all()
        for field in self.fields.values():
            field.widget.attrs.update({"class": "input"})


class DepartmentCreateForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["code", "name"]
        labels = {
            "code": _("Code"),
            "name": _("Name"),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "input"})


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["profile_image"]
        labels = {"profile_image": _("Profile picture")}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "input"})
