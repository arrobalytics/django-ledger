
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import BillModel
from graphene_django.filter import DjangoFilterConnectionField


class BillNode(DjangoObjectType):
    class Meta:
        model = BillModel
        filter_fields = {
            'vendor' : ['exact'],
            'xref' : ['exact', 'icontains', 'istartswith'],
            'date' : ['exact', 'icontains', 'istartswith'],
            'terms' : ['exact', 'icontains', 'istartswith'],
            'cash_account' : ['exact'],
            'prepaid_account' : ['exact'],
            'unearned_account' : ['exact'],
        }
        interfaces = (relay.Node,)

class Bill_list_Query(graphene.ObjectType):
    all_bills = DjangoFilterConnectionField(BillNode, slug_name=graphene.String(required=True))

    def resolve_all_bills(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return BillModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).select_related('vendor').order_by('-updated')
        else:
            return BillModel.objects.none()

