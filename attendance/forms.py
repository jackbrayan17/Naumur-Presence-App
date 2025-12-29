from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False, label=_("Keep me signed in"), widget=forms.CheckboxInput()
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "input"})
        self.fields["password"].widget.attrs.update({"class": "input"})
