import graphene
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from django_ledger.contrib.django_ledger_graphene.accounts.schema import Accountlist_Query
from django_ledger.contrib.django_ledger_graphene.bank_account.schema import Bank_account_Query
from django_ledger.contrib.django_ledger_graphene.bill.schema import Bill_list_Query
from django_ledger.contrib.django_ledger_graphene.coa.schema import ChartOfAccountsQuery
from django_ledger.contrib.django_ledger_graphene.entity.schema import Entity_Query
from django_ledger.contrib.django_ledger_graphene.item.schema import UnitOfMeasureQuery
from django_ledger.contrib.django_ledger_graphene.journal_entry.schema import JournalEntryQuery
from django_ledger.contrib.django_ledger_graphene.ledger.schema import LedgerQuery
from django_ledger.contrib.django_ledger_graphene.purchase_order.schema import PurchaseOrderQuery
from django_ledger.contrib.django_ledger_graphene.transaction.schema import TransactionsQuery
from django_ledger.contrib.django_ledger_graphene.unit.schema import EntityUnitQuery
from django_ledger.contrib.django_ledger_graphene.vendor.schema import VendorsQuery
from .auth.mutations import AuthMutation
from .auth.schema import QueryUser
from .bank_account.mutations import BankAccountMutations
from .customers.mutations import CustomerMutations
from .customers.schema import CustomerQuery

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
