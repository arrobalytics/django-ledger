"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.
"""

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, CreateView, DetailView
from django.views.generic import RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.account import AccountModelUpdateForm, AccountModelCreateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityModel, ChartOfAccountModel
from django_ledger.models.accounts import AccountModel
from django_ledger.views.mixins import (
    YearlyReportMixIn, MonthlyReportMixIn, QuarterlyReportMixIn, DjangoLedgerSecurityMixIn,
    BaseDateNavigationUrlMixIn, EntityUnitMixIn, DateReportMixIn
)


class BaseAccountModelBaseView(DjangoLedgerSecurityMixIn):
    queryset = None
    coa_model = None

    def get_authorized_entity_queryset(self):
        qs = super().get_authorized_entity_queryset()
        return qs.select_related('admin', 'default_coa', 'default_coa__entity')

    def get_coa_model(self):
        if not self.coa_model:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.coa_model = entity_model.chartofaccountmodel_set.get(slug__exact=self.kwargs['coa_slug'])
        return self.coa_model

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            coa_slug = self.kwargs['coa_slug']

            coa_model, account_model_qs = entity_model.get_coa_accounts(
                coa_model=entity_model.default_coa if coa_slug == entity_model.default_coa_slug else coa_slug,
                return_coa_model=True,
                active=False
            )

            account_model_qs = account_model_qs.select_related(
                'coa_model',
                'coa_model__entity'
            ).order_by(
                'coa_model', 'role', 'code'
            ).not_coa_root()

            self.coa_model = coa_model
            self.queryset = account_model_qs

        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['coa_model'] = self.get_coa_model()
        return context


# Account Views ----
class AccountModelListView(BaseAccountModelBaseView, ListView):
    template_name = 'django_ledger/account/account_list.html'
    context_object_name = 'accounts'
    PAGE_TITLE = _('Entity Accounts')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    active_only = False

    def get_queryset(self):
        qs = super().get_queryset()
        if self.active_only:
            qs = qs.active()
        return qs



    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        chart_of_accounts_model: ChartOfAccountModel = self.get_coa_model()
        if not chart_of_accounts_model.is_active():
            messages.error(request, _('WARNING: The chart of accounts list is inactive.'), extra_tags='is-danger')
        return response



class AccountModelCreateView(BaseAccountModelBaseView, CreateView):
    template_name = 'django_ledger/account/account_create.html'
    PAGE_TITLE = _('Create Account')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'ic:twotone-account-tree'

    }

    def get_form(self, form_class=None):
        return AccountModelCreateForm(
            coa_model=self.get_coa_model(),
            **self.get_form_kwargs()
        )

    def get_initial(self):
        return {
            'coa_model': self.get_coa_model(),
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        coa_model = self.get_coa_model()
        context['coa_model'] = coa_model
        context['header_subtitle'] = f'CoA: {coa_model.name}'
        return context

    def form_valid(self, form: AccountModelCreateForm):
        account_model: AccountModel = form.save(commit=False)
        coa_model = account_model.coa_model
        coa_model.insert_account(account_model=account_model)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        coa_model: ChartOfAccountModel = self.get_coa_model()
        return coa_model.get_account_list_url()


class AccountModelUpdateView(BaseAccountModelBaseView, UpdateView):
    context_object_name = 'account'
    template_name = 'django_ledger/account/account_update.html'
    slug_url_kwarg = 'account_pk'
    slug_field = 'uuid'
    form_class = AccountModelUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Account')
        context['header_title'] = _(f'Update Account: {self.object.code} - {self.object.name}')
        context['header_subtitle_icon'] = 'ic:twotone-account-tree'
        return context

    def get_success_url(self):
        coa_model: ChartOfAccountModel = self.get_coa_model()
        return coa_model.get_account_list_url()


class AccountModelDetailView(BaseAccountModelBaseView, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        loc_date = get_localdate()
        entity_model: EntityModel = self.get_authorized_entity_instance()
        return reverse('django_ledger:account-detail-month',
                       kwargs={
                           'entity_slug': entity_model.slug,
                           'account_pk': self.kwargs['account_pk'],
                           'coa_slug': self.kwargs['coa_slug'],
                           'year': loc_date.year,
                           'month': loc_date.month,
                       })


class AccountModelYearDetailView(BaseAccountModelBaseView,
                                 BaseDateNavigationUrlMixIn,
                                 EntityUnitMixIn,
                                 YearlyReportMixIn,
                                 DetailView):
    context_object_name = 'account'
    template_name = 'django_ledger/account/account_detail.html'
    slug_url_kwarg = 'account_pk'
    slug_field = 'uuid'
    DEFAULT_TXS_DAYS = 30
    extra_context = {
        'DEFAULT_TXS_DAYS': DEFAULT_TXS_DAYS,
        'header_subtitle_icon': 'ic:round-account-tree'
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account_model: AccountModel = context['object']
        context['header_title'] = f'Account {account_model.code} - {account_model.name}'
        context['page_title'] = f'Account {account_model.code} - {account_model.name}'
        txs_qs = account_model.transactionmodel_set.all().posted().order_by(
            'journal_entry__timestamp'
        ).select_related(
            'journal_entry',
            'journal_entry__entity_unit',
            'journal_entry__ledger__billmodel',
            'journal_entry__ledger__invoicemodel',
        )
        txs_qs = txs_qs.from_date(self.get_from_date())
        txs_qs = txs_qs.to_date(self.get_to_date())
        context['transactions'] = txs_qs
        return context


class AccountModelQuarterDetailView(QuarterlyReportMixIn, AccountModelYearDetailView):
    """
    Account Model Quarter Detail View
    """


class AccountModelMonthDetailView(MonthlyReportMixIn, AccountModelYearDetailView):
    """
    Account Model Month Detail View
    """


class AccountModelDateDetailView(DateReportMixIn, AccountModelYearDetailView):
    """
    Account Model Date Detail View
    """


# ACTIONS...
class AccountModelModelActionView(BaseAccountModelBaseView,
                                  RedirectView,
                                  SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'account_pk'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        account_model: AccountModel = self.get_object()
        return account_model.get_coa_account_list_url()

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(AccountModelModelActionView, self).get(request, *args, **kwargs)
        account_model: AccountModel = self.get_object()

        try:
            getattr(account_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(
                request,
                message=e.message,
                level=messages.ERROR,
                extra_tags='is-danger'
            )
        return response
