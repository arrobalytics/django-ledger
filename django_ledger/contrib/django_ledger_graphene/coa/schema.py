import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from django_ledger.models import ChartOfAccountModel


class ChartOfAccountsModelType(DjangoObjectType):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'uuid',
            'slug',
            'name',
            'locked'
        ]
        interfaces = (relay.Node,)

# class ChartOfAccountsModelQuery(graphene.ObjectType):
#     all_coa = graphene.List(ChartOfAccountsModelType, slug=graphene.String(required=True))
#
#     def resolve_all_coa(self, info, slug, **kwargs):
#
#         if info.context.user.is_authenticated:
#             return ChartOfAccountModel.objects.for_entity(
#                 entity_slug=slug,
#                 user_model=info.context.user,
#             )
#         else:
#             return ChartOfAccountModel.objects.none()
