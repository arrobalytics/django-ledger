
import graphene
from graphene_django import DjangoObjectType
from django_ledger.models import AccountModel


class AccountList(DjangoObjectType):
    class Meta:
        model = AccountModel

class Accountlist_Query(graphene.ObjectType):
    all_accounts = graphene.List(AccountList, slug_name=graphene.String(required=True))

    def resolve_all_accounts(self, info, slug_name):
        if info.context.user.is_authenticated:
            return AccountModel.on_coa.for_entity(
            entity_slug=slug_name,
            user_model=info.context.user,
        ).select_related('parent').order_by('code')
        else:
            return AccountModel.objects.none()

