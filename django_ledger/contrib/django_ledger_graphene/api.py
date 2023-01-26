import graphene
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from django_ledger.contrib.django_ledger_graphene.coa.schema import ChartOfAccountsQuery
from django_ledger.contrib.django_ledger_graphene.entity.schema import EntityModelQuery

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    # CustomerQuery,
    # Bill_list_Query,
    # Accountlist_Query,
    # Bank_account_Query        ,
    # ChartOfAccountsQuery,
    EntityModelQuery,
    ChartOfAccountsQuery
    # UnitOfMeasureQuery,
    # VendorsQuery,
    # EntityUnitQuery,
    # LedgerQuery,
    # TransactionsQuery,
    # JournalEntryQuery,
    # PurchaseOrderQuery,
    # QueryUser,
):
    pass


class Mutation(
    # CustomerMutations,
    # BankAccountMutations,
    # AuthMutation,
):
    pass


schema = graphene.Schema(
    query=Query,
    # mutation=Mutation
)
