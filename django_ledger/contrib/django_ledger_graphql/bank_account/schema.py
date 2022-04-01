
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import BankAccountModel
from graphene_django.filter import DjangoFilterConnectionField


class BankaccountNode(DjangoObjectType):
    class Meta:
        model = BankAccountModel
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'account_type': ['exact', 'icontains', 'istartswith'],
            'account_number': ['exact', 'icontains', 'istartswith'],
            'routing_number': ['exact', 'icontains', 'istartswith'],
            'aba_number': ['exact', 'icontains', 'istartswith'],
            'cash_account': ['exact'],
            'active': ['exact']
        }
        interfaces = (relay.Node,)

class Bank_account_Query(graphene.ObjectType):
    all_bankaccounts = DjangoFilterConnectionField(BankaccountNode, slug_name=graphene.String(required=True))

    def resolve_all_bankaccounts(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return BankAccountModel.objects.for_entity(
            entity_slug=slug_name,
            user_model=info.context.user
        ).select_related('cash_account')
        else:
            return BankAccountModel.objects.none()

