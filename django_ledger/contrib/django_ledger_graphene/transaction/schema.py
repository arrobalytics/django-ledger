import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from django_ledger.models import TransactionModel


class TransactionNode(DjangoObjectType):
    class Meta:
        model = TransactionModel
        filter_fields = {
            'journal_entry': ['exact'],
            'account': ['exact'],
            'tx_type': ['exact', 'icontains', 'istartswith'],
            'amount': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)
class TransactionsQuery(graphene.ObjectType):
    all_transactions = DjangoFilterConnectionField(TransactionNode, slug_name=graphene.String(required=True),
     pk_je=graphene.UUID(), pk_ledger=graphene.UUID())

    def resolve_all_transactions(self, info, slug_name, pk_je, pk_ledger, **kwargs):
        if info.context.user.is_authenticated:
            return TransactionModel.objects.for_journal_entry(
                entity_slug=slug_name,
                user_model=info.context.user,
                je_model=pk_je,
                ledger_model=pk_ledger
            ).order_by('account__code')
        else:
            return TransactionModel.objects.none()

