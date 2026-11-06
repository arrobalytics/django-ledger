"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Bank Account views grouped by CRUD + Actions.

  * CREATE   — BankAccountModelCreateView
  * RETRIEVE — BankAccountModelListView
  * UPDATE   — BankAccountModelUpdateView
  * ACTIONS  — activate / deactivate via BaseBankAccountModelActionView
"""
from typing import Optional

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView

from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm
from django_ledger.models import EntityModel
from django_ledger.models.bank_account import BankAccountModel, BankAccountModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionView


class BankAccountModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped bank account queryset shared by all bank-account CRUD/action views."""

    queryset: Optional[BankAccountModelQuerySet] = None

    def get_queryset(self) -> BankAccountModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: BankAccountModelQuerySet = entity_model.bankaccountmodel_set.select_related(
                'account_model', 'entity_model'
            )
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE (List)
# -----------------
class BankAccountModelListView(BankAccountModelModelBaseView, ListView):
    template_name = 'django_ledger/bank_account/bank_account_list.html'
    PAGE_TITLE = _('Bank Accounts')
    context_object_name = 'bank_accounts'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }


# -----------------
# CREATE
# -----------------
class BankAccountModelCreateView(BankAccountModelModelBaseView, CreateView):
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
        bank_account_model.configure(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            commit=False)
        return super(BankAccountModelCreateView, self).form_valid(form)


# -----------------
# UPDATE
# -----------------
class BankAccountModelUpdateView(BankAccountModelModelBaseView, UpdateView):
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


# -----------------
# ACTIONS (activate / deactivate)
# -----------------
class BaseBankAccountModelActionView(BankAccountModelModelBaseView, DjangoLedgerActionView):
    """
    Shared bank-account action endpoint (activate / deactivate).

    Runs the configured BankAccountModel method and redirects to the bank
    account list. Requires POST by default.
    """

    pk_url_kwarg = 'bank_account_pk'

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': kwargs['entity_slug']
                       })


class BankAccountModelActionMarkAsActiveView(BaseBankAccountModelActionView):
    """Activates a bank account so it can be used for payments and imports."""

    action_name = 'mark_as_active'


class BankAccountModelActionMarkAsInactiveView(BaseBankAccountModelActionView):
    """Deactivates a bank account without deleting its historical data."""

    action_name = 'mark_as_inactive'
