
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import AccountModel
from graphene_django.filter import DjangoFilterConnectionField


class AccountNode(DjangoObjectType):
    class Meta:
        model = AccountModel
        filter_fields = {
            'parent': ['exact'],
            'code': ['exact', 'icontains', 'istartswith'],
            'name': ['exact', 'icontains', 'istartswith'],
            'locked': ['exact'],
            'active': ['exact']
        }
        interfaces = (relay.Node,)


class Accountlist_Query(graphene.ObjectType):
    all_accounts = DjangoFilterConnectionField(AccountNode, slug_name=graphene.String(required=True))

    def resolve_all_accounts(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return AccountModel.objects.for_entity(
            entity_slug=slug_name,
            user_model=info.context.user,
        ).select_related('parent').order_by('code')
        else:
            return AccountModel.objects.none()

