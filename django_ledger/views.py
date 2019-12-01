from django.db.models import Q
from django.db.models import Value, CharField
from django.views.generic import ListView, DetailView

from django_ledger.models import EntityModel, ChartOfAccountModel, AccountModel


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


class ChartOfAccountsDetailView(DetailView):
    context_object_name = 'coa'
    slug_url_kwarg = 'coa_slug'
    template_name = 'django_ledger/coa_detail.html'

    def get_queryset(self):
        return ChartOfAccountModel.objects.filter(
            Q(user=self.request.user) |
            Q(entitymodel__entity_permissions__user=self.request.user)
        ).distinct().prefetch_related('acc_assignments__account')


class AccountModelDetailView(DetailView):
    context_object_name = 'account'
    pk_url_kwarg = 'account_pk'
    template_name = 'django_ledger/account_detail.html'

    def get_queryset(self):
        return AccountModel.objects.filter(
            Q(coa_assignments__coa__user=self.request.user) |
            Q(coa_assignments__coa__entitymodel__admin=self.request.user) |
            Q(coa_assignments__coa__entitymodel__managers__entity_permissions__user=self.request.user)
        ).distinct()
