import graphene

from django_ledger.contrib.django_ledger_graphene.coa.schema import ChartOfAccountsModelType
from django_ledger.contrib.django_ledger_graphene.entity.schema import EntityModelQuery, EntityModelType


class Query(
    EntityModelQuery,
    # ChartOfAccountsModelQuery
    # CustomerQuery,
    # Bill_list_Query,
    # Accountlist_Query,
    # Bank_account_Query        ,
    # ChartOfAccountsQuery,
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


# class Mutation(
#     # CustomerMutations,
#     # BankAccountMutations,
#     # AuthMutation,
# ):
#     pass


schema = graphene.Schema(
    types=[
        EntityModelType,
        ChartOfAccountsModelType
    ],
    query=Query,
    # mutation=Mutation
)
