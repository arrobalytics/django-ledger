import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import LedgerModel
from graphene_django.filter import DjangoFilterConnectionField


class LedgerNode(DjangoObjectType):
    class Meta:
        model = LedgerModel
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)


class LedgerQuery(graphene.ObjectType):
    all_ledger = DjangoFilterConnectionField(
        LedgerNode, slug_name=graphene.String(required=True))

    def resolve_all_vendors(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            sort = info.context.GET.get('sort')
            if not sort:
                sort = '-updated'
            return LedgerModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).order_by(sort)
        else:
            return LedgerModel.objects.none()
