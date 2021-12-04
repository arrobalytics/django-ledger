"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView

from django_ledger.forms.coa import ChartOfAccountsModelUpdateForm
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.views.mixins import LoginRequiredMixIn


class ChartOfAccountsUpdateView(LoginRequiredMixIn, UpdateView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/coa_update.html'
    form_class = ChartOfAccountsModelUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('CoA: ') + self.object.name
        context['header_title'] = _('CoA: ') + self.object.name
        return context

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': entity_slug
                       })

    def get_queryset(self):
        return ChartOfAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )
