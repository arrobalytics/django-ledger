from django.urls import reverse
import graphene
from django.utils.functional import SimpleLazyObject

from .customers.schema import CustomerQuery
from .customers.mutations import CustomerMutations
from .auth.mutations import AuthMutation
from .auth.schema import QueryUser
from .bank_account.mutations import BankAccountMutations
from django_ledger.contrib.django_ledger_graphql.bill.schema import Bill_list_Query
from django_ledger.contrib.django_ledger_graphql.accounts.schema import Accountlist_Query
from django_ledger.contrib.django_ledger_graphql.bank_account.schema import Bank_account_Query
from django_ledger.contrib.django_ledger_graphql.coa.schema import ChartOfAccountsQuery
from django_ledger.contrib.django_ledger_graphql.entity.schema import Entity_Query
from django_ledger.contrib.django_ledger_graphql.item.schema import UnitOfMeasureQuery

from django_ledger.contrib.django_ledger_graphql.vendor.schema import VendorsQuery
from django_ledger.contrib.django_ledger_graphql.unit.schema import EntityUnitQuery
from django_ledger.contrib.django_ledger_graphql.ledger.schema import LedgerQuery
from django_ledger.contrib.django_ledger_graphql.transaction.schema import TransactionsQuery
from django_ledger.contrib.django_ledger_graphql.journal_entry.schema import JournalEntryQuery
from django_ledger.contrib.django_ledger_graphql.purchase_order.schema import PurchaseOrderQuery

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    CustomerQuery,
    Bill_list_Query,
    Accountlist_Query,
    Bank_account_Query,
    ChartOfAccountsQuery,
    Entity_Query,
    UnitOfMeasureQuery,
    VendorsQuery,
    EntityUnitQuery,
    LedgerQuery,
    TransactionsQuery,
    JournalEntryQuery,
    PurchaseOrderQuery,
    QueryUser,

):
    pass

class Mutation(
    CustomerMutations,
    BankAccountMutations,
    AuthMutation,

):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
