from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView, RedirectView

from django_ledger.models import EntityModel


class RootUrlView(RedirectView):
    url = reverse_lazy('django_ledger:dashboard')


class DashboardView(TemplateView):
    template_name = 'django_ledger/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('dashboard')
        context['header_title'] = _('dashboard')
        context['entities'] = EntityModel.objects.for_user(
            user_model=self.request.user
        )
        return context
