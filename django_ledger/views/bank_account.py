"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView

from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.views.mixins import LoginRequiredMixIn


class BankAccountModelListView(LoginRequiredMixIn, ListView):
    template_name = 'django_ledger/bank_account_list.html'
    PAGE_TITLE = _('Bank Accounts')
    context_object_name = 'bank_accounts'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }

    def get_queryset(self):
        return BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('cash_account')


class BankAccountModelCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/bank_account_create.html'
    form_class = BankAccountCreateForm
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
            posted_ledger=True)
        bank_account_model.save()
        return HttpResponseRedirect(self.get_success_url())


class BankAccountModelUpdateView(LoginRequiredMixIn, UpdateView):
    template_name = 'django_ledger/bank_account_update.html'
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

    def get_queryset(self):
        return BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')

    def get_form(self, form_class=None):
        return BankAccountUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )
