from django.urls import reverse
import graphene
from django.utils.functional import SimpleLazyObject

from .customers.schema import CustomerQuery
from django_ledger.contrib.django_ledger_graphql.bill.schema import Bill_list_Query
from django_ledger.contrib.django_ledger_graphql.accounts.schema import Accountlist_Query
from django_ledger.contrib.django_ledger_graphql.bank_account.schema import Bank_account_Query
from django_ledger.contrib.django_ledger_graphql.coa.schema import ChartOfAccountsQuery
from django_ledger.contrib.django_ledger_graphql.entity.schema import Entity_Query
from django_ledger.contrib.django_ledger_graphql.item.schema import UnitOfMeasureQuery

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    CustomerQuery,
    Bill_list_Query,
    Accountlist_Query,
    Bank_account_Query,
    ChartOfAccountsQuery,
    Entity_Query,
    UnitOfMeasureQuery,
):
    pass


schema = graphene.Schema(query=Query)
