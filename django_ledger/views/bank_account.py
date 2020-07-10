from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse

from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.utils import new_bankaccount_protocol


class BankAccountModelListView(ListView):
    template_name = 'django_ledger/bank_account_list.html'
    PAGE_TITLE = _('Bank Accounts')
    context_object_name = 'bank_accounts'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        return BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('cash_account')


class BankAccountModelCreateView(CreateView):
    template_name = 'django_ledger/bank_account_create.html'
    form_class = BankAccountCreateForm
    PAGE_TITLE = _('Create Bank Account')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
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
        bank_account_model = form.instance
        form.instance = new_bankaccount_protocol(
            bank_account_model=bank_account_model,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user)
        return super().form_valid(form=form)


class BankAccountModelUpdateView(UpdateView):
    template_name = 'django_ledger/bank_account_update.html'
    slug_url_kwarg = 'bank_account_slug'
    PAGE_TITLE = _('Update Bank Account')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        return BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('cash_account')

    def get_form(self, form_class=None):
        return BankAccountUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )
