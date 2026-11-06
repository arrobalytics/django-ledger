"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Chart of Accounts views grouped by CRUD + Actions.

  * CREATE   — ChartOfAccountModelCreateView
  * RETRIEVE — ChartOfAccountModelListView
  * UPDATE   — ChartOfAccountModelUpdateView
  * ACTIONS  — mark default / active / inactive via CharOfAccountModelActionView
"""

from typing import Optional

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, ListView, CreateView

from django_ledger.forms.chart_of_accounts import ChartOfAccountsModelUpdateForm, ChartOfAccountsModelCreateForm
from django_ledger.models import EntityModel, ChartOfAccountModelQuerySet
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionView


class ChartOfAccountModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped chart-of-accounts queryset shared by all CoA CRUD/action views."""

    queryset: Optional[ChartOfAccountModelQuerySet] = None

    def get_queryset(self) -> ChartOfAccountModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: ChartOfAccountModelQuerySet = entity_model.chartofaccountmodel_set.all().order_by('-updated')
            self.queryset = qs
        return self.queryset


# -----------------
# RETRIEVE (List)
# -----------------
class ChartOfAccountModelListView(ChartOfAccountModelModelBaseView, ListView):
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


# -----------------
# CREATE
# -----------------
class ChartOfAccountModelCreateView(ChartOfAccountModelModelBaseView, CreateView):
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
            entity_model=self.get_authorized_entity_instance(), **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['header_subtitle'] = f'New Chart of Accounts: {self.AUTHORIZED_ENTITY_MODEL.name}'
        context['header_subtitle_icon'] = 'gravity-ui:hierarchy'
        return context

    def get_success_url(self):
        chart_of_accounts_model: ChartOfAccountModel = self.object
        return chart_of_accounts_model.get_coa_list_url()


# -----------------
# UPDATE
# -----------------
class ChartOfAccountModelUpdateView(ChartOfAccountModelModelBaseView, UpdateView):
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


# -----------------
# ACTIONS (default / active / inactive)
# -----------------
class CharOfAccountModelActionView(
    ChartOfAccountModelModelBaseView,
    DjangoLedgerActionView,
):
    """
    Shared Chart of Accounts action endpoint.

    Concrete subclasses set ``action_name`` (mark default, active, or inactive).
    On success a flash message confirms the change for the authorized entity,
    then the user is sent back to the CoA list. Requires POST by default.
    """

    slug_url_kwarg = 'coa_slug'

    def get_redirect_url(self, *args, **kwargs):
        chart_of_accounts_model: ChartOfAccountModel = self.get_object()
        return chart_of_accounts_model.get_coa_list_url()

    def handle_action_success(self, request, model_instance):
        messages.add_message(
            request,
            level=messages.SUCCESS,
            extra_tags='is-success',
            message=_(
                'Successfully updated {} Default Chart of Account to '.format(self.AUTHORIZED_ENTITY_MODEL.name)
                + '{}'.format(model_instance.name)
            ),
        )


class CharOfAccountModelActionMarkAsDefaultView(CharOfAccountModelActionView):
    """Sets the chart of accounts as the entity's default CoA."""

    action_name = 'mark_as_default'


class CharOfAccountModelActionMarkAsActiveView(CharOfAccountModelActionView):
    """Marks the chart of accounts as active for day-to-day use."""

    action_name = 'mark_as_active'


class CharOfAccountModelActionMarkAsInactiveView(CharOfAccountModelActionView):
    """Marks the chart of accounts as inactive without deleting accounts."""

    action_name = 'mark_as_inactive'
