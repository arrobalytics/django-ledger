"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from typing import Optional

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm
from django_ledger.models import EntityModel
from django_ledger.models.bank_account import BankAccountModel, BankAccountModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionViewMixIn


class BankAccountModelModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Shared bank-account queryset scoped to the authorized business.
    """
    queryset: Optional[BankAccountModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.queryset = entity_model.bankaccountmodel_set.select_related('account_model', 'entity_model')
        return super().get_queryset()


class BankAccountModelListView(BankAccountModelModelBaseView, ListView):
    """
    Lists bank accounts linked to the business so you can see cash accounts
    and which ones are active for imports and payments.
    """
    template_name = 'django_ledger/bank_account/bank_account_list.html'
    PAGE_TITLE = _('Bank Accounts')
    context_object_name = 'bank_accounts'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }


class BankAccountModelCreateView(BankAccountModelModelBaseView, CreateView):
    """
    Creates a bank account and links it to a cash ledger account.
    """
    template_name = 'django_ledger/bank_account/bank_account_create.html'
    PAGE_TITLE = _('Create Bank Account')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }

    def get_form(self, form_class=None):
        return BankAccountCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        bank_account_model: BankAccountModel = form.save(commit=False)
        entity_model: EntityModel = self.get_authorized_entity_instance()
        bank_account_model.configure(
            entity_slug=entity_model,
            user_model=self.request.user,
            commit=False)
        return super().form_valid(form)


class BankAccountModelUpdateView(BankAccountModelModelBaseView, UpdateView):
    """
    Updates bank account details and the linked cash account.
    """
    template_name = 'django_ledger/bank_account/bank_account_update.html'
    pk_url_kwarg = 'bank_account_pk'
    PAGE_TITLE = _('Update Bank Account')
    context_object_name = 'bank_account'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }

    def get_success_url(self):
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return BankAccountUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )


class BaseBankAccountModelActionView(
    BankAccountModelModelBaseView,
    DjangoLedgerActionViewMixIn,
    SingleObjectMixin,
    View,
):
    """
    Applies bank-account actions such as marking an account active or inactive.
    """
    pk_url_kwarg = 'bank_account_pk'
    action_name = None
    commit = True

    def get_redirect_url(self) -> str:
        return reverse(
            'django_ledger:bank-account-list',
            kwargs={'entity_slug': self.kwargs['entity_slug']},
        )


class BankAccountModelActionMarkAsActiveView(BaseBankAccountModelActionView):
    """
    Marks a bank account as active.
    """
    action_name = 'mark_as_active'


class BankAccountModelActionMarkAsInactiveView(BaseBankAccountModelActionView):
    """
    Marks a bank account as inactive.
    """
    action_name = 'mark_as_inactive'
