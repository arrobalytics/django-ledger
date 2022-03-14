
import graphene
from graphene_django import DjangoObjectType
from django_ledger.models import ChartOfAccountModel


class CoaList(DjangoObjectType):
    class Meta:
        model = ChartOfAccountModel


class ChartOfAccountsQuery(graphene.ObjectType):
    all_coa = graphene.List(CoaList, slug_name=graphene.String(required=True))

    def resolve_all_coa(self, info, slug_name):
        if info.context.user.is_authenticated:
            return ChartOfAccountModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user,
            )
        else:
            return ChartOfAccountModel.objects.none()
