"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from django_ledger.forms.auth import LogInForm


class DjangoLedgerLoginView(LoginView):
    form_class = LogInForm
    template_name = 'django_ledger/auth/login.html'
    extra_context = {
        'page_title': _('Login')
    }

    def get_success_url(self):
        return reverse('django_ledger:home')


class DjangoLedgerLogoutView(LogoutView):
    next_page = reverse_lazy('django_ledger:login')
