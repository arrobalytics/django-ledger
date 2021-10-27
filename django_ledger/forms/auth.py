from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.forms import TextInput, CharField, PasswordInput
from django.utils.translation import gettext_lazy as _


class LogInForm(AuthenticationForm):
    username = UsernameField(
        widget=TextInput(
            attrs={
                'autofocus': True,
                'class': 'input',
                'id': 'djl-el-login-form-username-field'
            }))
    password = CharField(
        label=_("Password"),
        strip=False,
        widget=PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'class': 'input',
                'id': 'djl-el-login-form-password-field'
            }),
    )
