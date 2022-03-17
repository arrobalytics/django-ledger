
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import ChartOfAccountModel
from graphene_django.filter import DjangoFilterConnectionField

class CoaNode(DjangoObjectType):
    class Meta:
        model = ChartOfAccountModel
        filter_fields = {
            'slug' : ['exact', 'icontains', 'istartswith'],
            'name' : ['exact', 'icontains', 'istartswith'],
            'description' : ['exact', 'icontains', 'istartswith']
        }
        interfaces = (relay.Node,)


class ChartOfAccountsQuery(graphene.ObjectType):
    all_coa = DjangoFilterConnectionField(CoaNode, slug_name=graphene.String(required=True))

    def resolve_all_coa(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return ChartOfAccountModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user,
            )
        else:
            return ChartOfAccountModel.objects.none()
