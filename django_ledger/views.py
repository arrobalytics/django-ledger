from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import (ListView, DetailView, UpdateView, CreateView, TemplateView, RedirectView)

from django_ledger.forms import (AccountModelDetailForm, AccountModelCreateForm, LedgerModelCreateForm,
                                 LedgerModelUpdateForm,
                                 JournalEntryModelForm, TransactionModelFormSet, EntityModelForm,
                                 ChartOfAccountsModelForm)
from django_ledger.models import (EntityModel, ChartOfAccountModel, TransactionModel,
                                  AccountModel, LedgerModel, JournalEntryModel)


class RootUrlView(RedirectView):
    url = reverse_lazy('django_ledger:entity-list')


# Entity Views ----
class EntityModelListView(ListView):
    template_name = 'django_ledger/entitiy_list.html'
    context_object_name = 'entities'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(managers__exact=self.request.user)
        )


class EntityModelDetailVew(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_detail.html'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The view queryset.
        """
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(managers__exact=self.request.user)
        ).select_related('coa')


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelForm

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def form_valid(self, form):
        user = self.request.user
        if user.is_authenticated:
            form.instance.admin = user
            self.object = form.save()
        return super().form_valid(form)


class EntityModelUpdateView(UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_update.html'
    form_class = EntityModelForm
    slug_url_kwarg = 'entity_slug'

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def get_queryset(self):
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(managers__exact=self.request.user)
        )


class EntityBalanceSheetView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The view queryset.
        """
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(managers__exact=self.request.user)
        )


class EntityIncomeStatementView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/income_statement.html'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The view queryset.
        """
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(entity_permissions__user=self.request.user)
        )


# CoA Views ---
class ChartOfAccountsDetailView(DetailView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/coa_detail.html'

    def get_queryset(self):
        return ChartOfAccountModel.objects.filter(
            Q(entity__admin=self.request.user) |
            Q(entity__managers__in=[self.request.user])
        ).distinct().prefetch_related('accounts')


class ChartOfAccountsUpdateView(UpdateView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/coa_update.html'
    form_class = ChartOfAccountsModelForm

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:entity-detail',
                       kwargs={
                           'entity_slug': entity_slug
                       })

    def get_queryset(self):
        return ChartOfAccountModel.objects.filter(
            Q(entity__admin=self.request.user) |
            Q(entity__managers__in=[self.request.user])
        ).distinct()


# Account Views ----
class AccountModelUpdateView(UpdateView):
    context_object_name = 'account'
    pk_url_kwarg = 'account_pk'
    template_name = 'django_ledger/account_update.html'
    form_class = AccountModelDetailForm

    def get_success_url(self):
        return reverse('django_ledger:coa-detail',
                       kwargs={
                           'coa_slug': self.object.coa.slug,
                           'entity_slug': self.object.coa.entity.slug
                       })

    def get_queryset(self):
        return AccountModel.objects.filter(
            Q(coa__entity__admin=self.request.user) |
            Q(coa__entity__managers__exact=self.request.user)
        ).select_related('coa').distinct()


class AccountModelCreateView(CreateView):
    template_name = 'django_ledger/account_create.html'
    form_class = AccountModelCreateForm

    def get_success_url(self):
        return reverse('django_ledger:coa-detail',
                       kwargs={
                           'coa_slug': self.object.coa.slug,
                           'entity_slug': self.object.coa.entity.slug
                       })


# Ledger Views ----
class LedgerModelListView(ListView):
    context_object_name = 'ledgers'
    template_name = 'django_ledger/ledger_list.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            Q(entity__admin=self.request.user) |
            Q(entity__managers__in=[self.request.user])
        )


class LedgerModelDetailView(DetailView):
    template_name = 'django_ledger/ledger_detail.html'
    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            Q(entity__admin=self.request.user) |
            Q(entity__managers__in=[self.request.user])
        ).prefetch_related('journal_entry', 'entity')


class LedgerModelCreateView(CreateView):
    template_name = 'django_ledger/ledger_create.html'
    form_class = LedgerModelCreateForm

    def get_initial(self):
        slug = self.kwargs.get('entity_slug')
        return {
            'entity': EntityModel.objects.get(slug=slug)
        }

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs.get('entity_slug')
                       })


class LedgerModelUpdateView(UpdateView):
    template_name = 'django_ledger/ledger_update.html'
    form_class = LedgerModelUpdateForm
    pk_url_kwarg = 'ledger_pk'
    context_object_name = 'ledger'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            Q(entity__admin=self.request.user) |
            Q(entity__managers__in=[self.request.user])
        )

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs.get('entity_slug')
                       })


class LedgerBalanceSheetView(DetailView):
    context_object_name = 'entity'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/balance_sheet.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            (
                    Q(entity__admin=self.request.user) |
                    Q(entity__managers__exact=self.request.user)
            )
        )


class LedgerIncomeStatementView(DetailView):
    context_object_name = 'entity'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/income_statement.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            (
                    Q(entity__admin=self.request.user) |
                    Q(entity__managers__exact=self.request.user)
            )
        )


# JE Views ---
class JournalEntryDetailView(DetailView):
    pk_url_kwarg = 'je_pk'
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_detail.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return JournalEntryModel.objects.filter(
            Q(ledger__entity__slug=entity_slug) &
            Q(ledger__entity__admin=self.request.user) |
            Q(ledger__entity__managers__in=[self.request.user])
        ).prefetch_related('txs', 'txs__account')


class JournalEntryUpdateView(UpdateView):
    pk_url_kwarg = 'je_pk'
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_update.html'
    form_class = JournalEntryModelForm

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return JournalEntryModel.objects.filter(
            Q(ledger__entity__slug=entity_slug) &
            Q(ledger__entity__admin=self.request.user) |
            Q(ledger__entity__managers__in=[self.request.user])
        ).prefetch_related('txs', 'txs__account')


class JournalEntryCreateView(CreateView):
    form_class = JournalEntryModelForm
    template_name = 'django_ledger/je_create.html'

    def get_initial(self):
        ledger_pk = self.kwargs.get('ledger_pk')
        return {
            'ledger': LedgerModel.objects.get(pk=ledger_pk)
        }

    def get_success_url(self):
        return reverse('django_ledger:ledger-detail',
                       kwargs={
                           'entity_slug': self.kwargs.get('entity_slug'),
                           'ledger_pk': self.kwargs.get('ledger_pk')
                       })


# TXS View ---
class TXSView(TemplateView):
    template_name = 'django_ledger/txs.html'

    def get_queryset(self):
        kwargs = self.kwargs
        return TransactionModel.objects.filter(
            Q(journal_entry_id=kwargs.get('je_pk')) &
            Q(journal_entry__ledger__entity__slug=kwargs.get('entity_slug')) &
            (
                    Q(journal_entry__ledger__entity__admin=self.request.user) |
                    Q(journal_entry__ledger__entity__managers__exact=self.request.user)
            )
        ).order_by('account__code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # txs_api_url = reverse('django_ledger:txs-api',
        #                       kwargs={
        #                           'entity_slug': kwargs['entity_slug'],
        #                           'ledger_pk': kwargs['ledger_pk'],
        #                           'je_pk': kwargs['je_pk'],
        #                       })
        txs_formset_url = reverse('django_ledger:txs',
                                  kwargs={
                                      'entity_slug': kwargs['entity_slug'],
                                      'ledger_pk': kwargs['ledger_pk'],
                                      'je_pk': kwargs['je_pk'],
                                  })
        # context['txs_api_url'] = txs_api_url
        context['txs_formset_url'] = txs_formset_url
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = TransactionModelFormSet(queryset=self.get_queryset())
        context['txs_formset'] = txs_formset
        return self.render_to_response(context)

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = TransactionModelFormSet(request.POST)
        je_model = JournalEntryModel.objects.filter(
            Q(id=context['je_pk']) &
            Q(ledger__entity__slug=context['entity_slug']) &
            (
                    Q(ledger__entity__admin__exact=self.request.user) |
                    Q(ledger__entity__managers__exact=self.request.user)
            )
        ).exists()
        if txs_formset.is_valid() and je_model:
            for f in txs_formset:
                f.instance.journal_entry_id = context['je_pk']
            txs_formset.save()
            txs_formset = TransactionModelFormSet(queryset=self.get_queryset())
            context['txs_formset'] = txs_formset
        else:
            context['txs_formset'] = txs_formset
        return self.render_to_response(context)

# class TXSAPIView(ListView):
#
#     def get_queryset(self):
#         kwargs = self.kwargs
#         return TransactionModel.objects.filter(
#             Q(journal_entry_id=kwargs.get('je_pk')) &
#             Q(journal_entry__ledger__entity__slug=kwargs.get('entity_slug')) &
#             (
#                     Q(journal_entry__ledger__entity__admin=self.request.user) |
#                     Q(journal_entry__ledger__entity__managers__exact=self.request.user)
#             )
#         ).select_related('account', 'journal_entry')
#
#     def get(self, request, *args, **kwargs):
#         data = list(self.get_queryset().values(
#             'id',
#             'account',
#             'account__name',
#             'account__code',
#             'tx_type',
#             'amount',
#             'description'
#         ))
#         return JsonResponse(data={'data': data})
