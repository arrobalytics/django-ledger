"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.
"""
from typing import Optional

from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import UpdateView, ListView, CreateView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.chart_of_accounts import ChartOfAccountsModelUpdateForm, ChartOfAccountsModelCreateForm
from django_ledger.models import EntityModel, ChartOfAccountModelQuerySet
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionViewMixIn


class ChartOfAccountModelModelBaseViewMixIn(DjangoLedgerSecurityMixIn):
    """
    Shared chart-of-accounts queryset scoped to the authorized business.
    """
    queryset: Optional[ChartOfAccountModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.queryset: ChartOfAccountModelQuerySet = entity_model.chartofaccountmodel_set.all().order_by('-updated')
        return self.queryset


class ChartOfAccountModelListView(ChartOfAccountModelModelBaseViewMixIn, ListView):
    """
    Lists chart-of-accounts books for the business so you can open, review,
    or switch between active and inactive account structures.
    """
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
    """
    Creates a new chart of accounts for the business.
    """
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
    """
    Updates the name and settings of an existing chart of accounts.
    """
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


class ChartOfAccountModelActionView(
    ChartOfAccountModelModelBaseViewMixIn,
    DjangoLedgerActionViewMixIn,
    SingleObjectMixin,
    View,
):
    """
    Applies chart-of-accounts actions such as setting the default book.
    """
    slug_url_kwarg = 'coa_slug'
    action_name = None
    commit = True

    def get_redirect_url(self) -> str:
        chart_of_accounts_model: ChartOfAccountModel = self.get_object()
        return chart_of_accounts_model.get_coa_list_url()

    def get_action_success_message(self) -> Optional[str]:
        if self.action_name != 'mark_as_default':
            return super().get_action_success_message()
        coa_model: ChartOfAccountModel = self.object
        return _(
            'Successfully updated {} Default Chart of Account to {}'.format(
                self.AUTHORIZED_ENTITY_MODEL.name,
                coa_model.name,
            )
        )


CharOfAccountModelActionView = ChartOfAccountModelActionView
