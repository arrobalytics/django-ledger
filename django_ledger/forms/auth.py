from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.forms import TextInput, CharField, PasswordInput
from django.utils.translation import gettext, gettext_lazy as _l


class LogInForm(AuthenticationForm):
    username = UsernameField(
        widget=TextInput(
            attrs={
                'autofocus': True,
                'class': 'input'
            }))
    password = CharField(
        label=_l("Password"),
        strip=False,
        widget=PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'class': 'input'
            }),
    )
