"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.
"""

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, ListView, RedirectView, CreateView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.chart_of_accounts import ChartOfAccountsModelUpdateForm, ChartOfAccountsModelCreateForm
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class ChartOfAccountModelModelBaseViewMixIn(DjangoLedgerSecurityMixIn):
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model = self.get_authorized_entity_instance()
            self.queryset = entity_model.chartofaccountmodel_set.all().order_by('-updated')
        return super().get_queryset()


class ChartOfAccountModelListView(ChartOfAccountModelModelBaseViewMixIn, ListView):
    template_name = 'django_ledger/chart_of_accounts/coa_list.html'
    context_object_name = 'coa_list'
    inactive = False

    def get_queryset(self):
        qs = super().get_queryset()
        if self.inactive:
            return qs.filter(active=False)
        return qs.active()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['inactive'] = self.inactive
        context['header_subtitle'] = self.AUTHORIZED_ENTITY_MODEL.name
        context['header_subtitle_icon'] = 'gravity-ui:hierarchy'
        context['page_title'] = 'Inactive Chart of Account List' if self.inactive else 'Chart of Accounts List'
        context['header_title'] = 'Inactive Chart of Account List' if self.inactive else 'Chart of Accounts List'
        return context


class ChartOfAccountModelCreateView(ChartOfAccountModelModelBaseViewMixIn, CreateView):
    template_name = 'django_ledger/chart_of_accounts/coa_create.html'
    extra_context = {
        'header_title': _('Create Chart of Accounts'),
        'page_title': _('Create Chart of Account'),
    }

    def get_initial(self):
        return {
            'entity': self.get_authorized_entity_instance(),
        }

    def get_form(self, form_class=None):
        return ChartOfAccountsModelCreateForm(
            entity_model=self.get_authorized_entity_instance(),
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['header_subtitle'] = f'New Chart of Accounts: {self.AUTHORIZED_ENTITY_MODEL.name}'
        context['header_subtitle_icon'] = 'gravity-ui:hierarchy'
        return context

    def get_success_url(self):
        chart_of_accounts_model: ChartOfAccountModel = self.object
        return chart_of_accounts_model.get_coa_list_url()


class ChartOfAccountModelUpdateView(ChartOfAccountModelModelBaseViewMixIn, UpdateView):
    context_object_name = 'coa_model'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/chart_of_accounts/coa_update.html'
    form_class = ChartOfAccountsModelUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chart_of_accounts_model: ChartOfAccountModel = self.object
        context['page_title'] = f'Update Chart of Account {chart_of_accounts_model.name}'
        context['header_title'] = f'Update Chart of Account {chart_of_accounts_model.name}'
        return context

    def get_success_url(self):
        chart_of_accounts_model: ChartOfAccountModel = self.object
        return chart_of_accounts_model.get_coa_list_url()


# todo: centralize this functionality into a separate class for ALL Action views...
class CharOfAccountModelActionView(ChartOfAccountModelModelBaseViewMixIn,
                                   RedirectView,
                                   SingleObjectMixin):
    http_method_names = ['get']
    slug_url_kwarg = 'coa_slug'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        chart_of_accounts_model: ChartOfAccountModel = self.get_object()
        return chart_of_accounts_model.get_coa_list_url()

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
