from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import ListView, DetailView, UpdateView, CreateView

from django_ledger.forms import EntityModelForm, EntityModelCreateForm
from django_ledger.models import EntityModel, TransactionModel
from django_ledger.models.utils import populate_default_coa
from django_ledger.models_abstracts.accounts import BS_ROLES, ACCOUNT_TERRITORY


def txs_digest(tx: dict) -> dict:
    tx['role_bs'] = BS_ROLES.get(tx['account__role'])
    if tx['account__balance_type'] != tx['tx_type']:
        tx['amount'] = -tx['amount']
    if tx['account__balance_type'] != ACCOUNT_TERRITORY.get(tx['role_bs']):
        tx['amount'] = -tx['amount']
    return tx


# Entity Views ----
class EntityModelListView(ListView):
    template_name = 'django_ledger/entitiy_list.html'
    context_object_name = 'entities'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('my entities')
        context['header_title'] = _('my entities')
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityModelDetailVew(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['header_title'] = _l('entity') + ': ' + self.object.name

        txs_qs = TransactionModel.objects.for_user(
            user=self.request.user)
        txs_qs = txs_qs.filter(
            journal_entry__ledger__entity__slug__exact=self.kwargs['entity_slug']
        ).select_related('account').values('account__role',
                                           'tx_type',
                                           'account__balance_type',
                                           'amount')

        txs_qs = [txs_digest(txs) for txs in txs_qs]

        assets = [tx['amount'] for tx in txs_qs if tx['role_bs'] == 'assets']
        liabilities = [tx['amount'] for tx in txs_qs if tx['role_bs'] == 'liabilities']
        equity = [tx['amount'] for tx in txs_qs if tx['role_bs'] == 'equity']
        income = [tx['amount'] for tx in txs_qs if tx['account__role'] == 'in']
        expenses = [-tx['amount'] for tx in txs_qs if tx['account__role'] == 'ex']

        context['asset_amount'] = sum(assets)
        context['liability_amount'] = sum(liabilities)
        context['equity_amount'] = sum(equity)
        context['income_amount'] = sum(income)
        context['expenses_amount'] = sum(expenses)
        context['earnings_amount'] = context['income_amount'] - context['expenses_amount']

        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(
            user=self.request.user).select_related('coa')


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelCreateForm
    extra_context = {
        'header_title': _('create entity'),
        'page_title': _('create entity')
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _l('create entity')
        context['header_title'] = _l('create entity')
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def form_valid(self, form):
        user = self.request.user
        if user.is_authenticated:
            form.instance.admin = user
            self.object = form.save()
            create_coa = form.cleaned_data.get('populate_default_coa')
            if create_coa:
                populate_default_coa(entity=self.object)
        return super().form_valid(form)


class EntityModelUpdateView(UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_update.html'
    form_class = EntityModelForm
    slug_url_kwarg = 'entity_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _l('update entity: ') + self.object.name
        context['header_title'] = _l('update entity: ') + self.object.name
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityBalanceSheetView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('balance sheet') + ': ' + self.object.name
        context['header_title'] = _('balance sheet') + ': ' + self.object.name
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityIncomeStatementView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('income statement: ') + self.object.name
        context['header_title'] = _('income statement: ') + self.object.name
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)
