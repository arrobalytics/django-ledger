
import graphene
from graphene_django import DjangoObjectType
from django_ledger.models import BankAccountModel


class Bank_accountList(DjangoObjectType):
    class Meta:
        model = BankAccountModel

class Bank_account_Query(graphene.ObjectType):
    all_bank_account_list = graphene.List(Bank_accountList, slug_name=graphene.String(required=True))

    def resolve_all_bank_account_list(self, info, slug_name):
        if info.context.user.is_authenticated:
            return BankAccountModel.objects.for_entity(
            entity_slug=slug_name,
            user_model=info.context.user
        ).select_related('cash_account')
        else:
            return BankAccountModel.objects.none()

