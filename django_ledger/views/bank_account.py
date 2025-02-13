"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm
from django_ledger.models import EntityModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class BankAccountModelModelBaseView(DjangoLedgerSecurityMixIn):
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.queryset = entity_model.bankaccountmodel_set.select_related('account_model', 'entity_model')
        return super().get_queryset()


class BankAccountModelListView(BankAccountModelModelBaseView, ListView):
    template_name = 'django_ledger/bank_account/bank_account_list.html'
    PAGE_TITLE = _('Bank Accounts')
    context_object_name = 'bank_accounts'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'clarity:bank-line'
    }


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


# ACTION VIEWS...
class BaseBankAccountModelActionView(BankAccountModelModelBaseView,
                                     RedirectView,
                                     SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'bank_account_pk'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': kwargs['entity_slug']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseBankAccountModelActionView, self).get(request, *args, **kwargs)
        ba_model: BankAccountModel = self.get_object()

        try:
            getattr(ba_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class BankAccountModelActionMarkAsActiveView(BaseBankAccountModelActionView):
    action_name = 'mark_as_active'


class BankAccountModelActionMarkAsInactiveView(BaseBankAccountModelActionView):
    action_name = 'mark_as_inactive'
