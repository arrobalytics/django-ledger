"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, CreateView, DetailView
from django.views.generic import RedirectView

from django_ledger.forms.account import AccountModelUpdateForm, AccountModelCreateForm, AccountModelCreateChildForm
from django_ledger.models import lazy_loader
from django_ledger.models.accounts import AccountModel
from django_ledger.views.mixins import (
    YearlyReportMixIn, MonthlyReportMixIn, QuarterlyReportMixIn, DjangoLedgerSecurityMixIn, SessionConfigurationMixIn,
    BaseDateNavigationUrlMixIn, EntityUnitMixIn, DateReportMixIn
)


# Account Views ----
class AccountModelListView(DjangoLedgerSecurityMixIn, ListView):
    template_name = 'django_ledger/account/account_list.html'
    context_object_name = 'accounts'
    PAGE_TITLE = _('Entity Accounts')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['asset_accounts'] = (a for a in qs if a.role_bs == 'assets')
        context['liability_accounts'] = (a for a in qs if a.role_bs == 'liabilities')
        context['equity_accounts'] = (a for a in qs if a.role_bs == 'equity')
        return context

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        ).order_by('code')


class AccountModelUpdateView(DjangoLedgerSecurityMixIn, UpdateView):
    context_object_name = 'account'
    template_name = 'django_ledger/account/account_update.html'
    slug_url_kwarg = 'account_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Account')
        context['header_title'] = _(f'Update Account: {self.object.code} - {self.object.name}')
        context['header_subtitle_icon'] = 'ic:twotone-account-tree'
        return context

    def get_form(self, form_class=None):
        return AccountModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': entity_slug,
                       })

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
        )


class AccountModelCreateView(DjangoLedgerSecurityMixIn, CreateView):
    template_name = 'django_ledger/account/account_create.html'
    PAGE_TITLE = _('Create Account')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'ic:twotone-account-tree'

    }

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_form(self, form_class=None):
        return AccountModelCreateForm(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        EntityModel = lazy_loader.get_entity_model()
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model: EntityModel = get_object_or_404(entity_model_qs, slug__exact=self.kwargs['entity_slug'])

        # parent_account_pk = self.kwargs.get('parent_account_pk')
        # if parent_account_pk:
        #     account_qs = self.get_queryset()
        #     parent_account_model = get_object_or_404(account_qs, uuid__exact=parent_account_pk)
        #     account.parent = parent_account_model
        #     account.role = parent_account_model.role

        # coa_qs = ChartOfAccountModel.objects.for_entity(user_model=self.request.user,
        #                                                 entity_slug=entity_slug)
        # coa_model = get_object_or_404(coa_qs, entity__slug__exact=entity_slug)

        account_model = AccountModel.add_root(**form.cleaned_data, coa_id=entity_model.default_coa_id)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': entity_slug,
                       })


class AccountModelCreateChildView(AccountModelCreateView):
    template_name = 'django_ledger/account/account_create_child.html'
    slug_url_kwarg = 'parent_account_pk'
    slug_field = 'uuid'
    PAGE_TITLE = _('Create Child Account')
    context_object_name = 'account'

    def get_context_data(self, **kwargs):
        context = super(AccountModelCreateChildView, self).get_context_data()
        obj: AccountModel = self.get_object()
        context['page_title'] = _('Create Child Account')
        context['header_title'] = _('Create Child Account - %s' % obj)
        context['header_subtitle_icon'] = 'ic:twotone-account-tree'
        context['account'] = obj
        return context

    def get_form(self, form_class=None):
        return AccountModelCreateChildForm(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            **self.get_form_kwargs()
        )


class AccountModelDetailView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        loc_date = localdate()
        return reverse('django_ledger:account-detail-month',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'account_pk': self.kwargs['account_pk'],
                           'year': loc_date.year,
                           'month': loc_date.month,
                       })


class AccountModelYearDetailView(DjangoLedgerSecurityMixIn,
                                 SessionConfigurationMixIn,
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
        account = self.object
        context = super().get_context_data(**kwargs)
        context['header_title'] = f'Account {account.code} - {account.name}'
        context['page_title'] = f'Account {account.code} - {account.name}'
        txs_qs = self.object.transactionmodel_set.order_by('-journal_entry__date')
        txs_qs = txs_qs.from_date(self.get_from_date())
        txs_qs = txs_qs.to_date(self.get_to_date())
        context['transactions'] = txs_qs
        return context

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
        ).prefetch_related('transactionmodel_set')


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
