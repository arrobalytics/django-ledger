from django.db.models import Q
from django.db.models import Value, CharField
from django.views.generic import ListView, DetailView, UpdateView, TemplateView

from django_ledger.forms import AccountModelForm, CoAAssignmentFormSet
from django_ledger.models import (EntityModel, ChartOfAccountModel, CoAAccountAssignments,
                                  AccountModel, LedgerModel, JournalEntryModel)


class EntityModelListView(ListView):
    template_name = 'django_ledger/entities.html'
    context_object_name = 'entities'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        owned = EntityModel.objects.filter(
            admin=self.request.user).annotate(
            user_role=Value('owned', output_field=CharField())
        )
        managed = EntityModel.objects.filter(entity_permissions__user=self.request.user).annotate(
            user_role=Value('managed', output_field=CharField())
        )
        return owned.union(managed).distinct()


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
            Q(entity_permissions__user=self.request.user)
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
            Q(entity_permissions__user=self.request.user)
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


class ChartOfAccountsListView(ListView):
    template_name = 'django_ledger/coa_list.html'
    context_object_name = 'coas'

    def get_queryset(self):
        return ChartOfAccountModel.objects.filter(
            Q(user=self.request.user) |
            Q(entitymodel__entity_permissions__user=self.request.user)
        ).distinct()


class ChartOfAccountsDetailView(DetailView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/coa_detail.html'

    def get_queryset(self):
        return ChartOfAccountModel.objects.filter(
            Q(user=self.request.user) |
            Q(entitymodel__entity_permissions__user=self.request.user)
        ).distinct().prefetch_related('acc_assignments__account')


class ChartOfAccountAssignmentsView(TemplateView):
    context_object_name = 'assignments'
    template_name = 'django_ledger/coa_assignments.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['formset'] = CoAAssignmentFormSet(queryset=self.get_queryset())
        return self.render_to_response(context=context)

    def post(self, *args, **kwargs):
        context = self.get_context_data()
        formset = CoAAssignmentFormSet(self.request.POST)
        if formset.is_valid():
            formset.save()
        context['formset'] = formset
        return self.render_to_response(context=context)

    def get_queryset(self):
        coa_slug = self.kwargs['coa_slug']
        return CoAAccountAssignments.objects.filter(
            Q(coa__user=self.request.user) |
            Q(coa__entitymodel__managers__entity_permissions__user=self.request.user) &
            Q(coa__slug__iexact=coa_slug)
        ).select_related('coa', 'account')


class AccountModelDetailView(UpdateView):
    context_object_name = 'account'
    pk_url_kwarg = 'account_pk'
    template_name = 'django_ledger/account_detail.html'
    form_class = AccountModelForm

    def get_queryset(self):
        return AccountModel.objects.filter(
            Q(coa_assignments__coa__user=self.request.user) |
            Q(coa_assignments__coa__entitymodel__admin=self.request.user) |
            Q(coa_assignments__coa__entitymodel__managers__entity_permissions__user=self.request.user)
        ).distinct()


class LedgerModelListView(ListView):
    context_object_name = 'ledgers'
    template_name = 'django_ledger/ledger.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.filter(
            Q(entity__slug=entity_slug) &
            Q(entity__admin=self.request.user) |
            Q(entity__managers__entity_permissions__user=self.request.user)
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
            Q(entity__managers__entity_permissions__user=self.request.user)
        ).prefetch_related('journal_entry', 'entity')


class JournalEntryDetail(DetailView):
    pk_url_kwarg = 'je_pk'
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/journal_entry_detail.html'

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return JournalEntryModel.objects.filter(
            Q(ledger__entity__slug=entity_slug) &
            Q(ledger__entity__admin=self.request.user) |
            Q(ledger__entity__managers__entity_permissions__user=self.request.user)
        ).prefetch_related('txs', 'txs__account')
