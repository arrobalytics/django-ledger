"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.coa import ChartOfAccountsModelUpdateForm
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class ChartOfAccountsModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = ChartOfAccountModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
            ).select_related('entity').order_by('-updated')
        return super().get_queryset()


class ChartOfAccountsListView(DjangoLedgerSecurityMixIn, ChartOfAccountsModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/chart_of_accounts/coa_list.html'
    extra_context = {
        'header_title': _('Chart of Account List'),
    }
    context_object_name = 'coa_list'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['header_subtitle'] = self.AUTHORIZED_ENTITY_MODEL.name
        context['header_subtitle_icon'] = 'gravity-ui:hierarchy'
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(
            accountmodel_total__count=Count(
                'accountmodel',
                # excludes coa root accounts...
                filter=Q(accountmodel__depth__gt=2)
            ),
            accountmodel_locked__count=Count(
                'accountmodel',
                # excludes coa root accounts...
                filter=Q(accountmodel__depth__gt=2) & Q(accountmodel__locked=True)
            ),
            accountmodel_active__count=Count(
                'accountmodel',
                # excludes coa root accounts...
                filter=Q(accountmodel__depth__gt=2) & Q(accountmodel__active=True)
            ),

        )


class ChartOfAccountsUpdateView(DjangoLedgerSecurityMixIn, ChartOfAccountsModelModelViewQuerySetMixIn, UpdateView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/chart_of_accounts/coa_update.html'
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


# todo: centralize this functionality into a separate class for ALL Action views...
class CharOfAccountModelActionView(DjangoLedgerSecurityMixIn,
                                   RedirectView,
                                   ChartOfAccountsModelModelViewQuerySetMixIn,
                                   SingleObjectMixin):
    http_method_names = ['get']
    slug_url_kwarg = 'coa_slug'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:coa-list',
                       kwargs={
                           'entity_slug': kwargs['entity_slug']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(CharOfAccountModelActionView, self).get(request, *args, **kwargs)
        coa_model: ChartOfAccountModel = self.get_object()

        try:
            getattr(coa_model, self.action_name)(commit=self.commit, **kwargs)
            messages.add_message(request, level=messages.SUCCESS, extra_tags='is-success',
                                 message=_('Successfully updated {} Default Chart of Account to '.format(
                                     self.AUTHORIZED_ENTITY_MODEL.name) +
                                           '{}'.format(coa_model.name)))
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response
