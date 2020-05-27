from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse, reverse_lazy

from django_ledger.forms.auth import LogInForm


class DjangoLedgerLoginView(LoginView):
    form_class = LogInForm
    template_name = 'django_ledger/auth/login.html'

    def get_success_url(self):
        return reverse('django_ledger:dashboard')


class DjangoLedgerLogoutView(LogoutView):
    next_page = reverse_lazy('django_ledger:login')
