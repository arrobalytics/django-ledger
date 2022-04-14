import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import PurchaseOrderModel
from graphene_django.filter import DjangoFilterConnectionField


class PurchaseOrderNode(DjangoObjectType):
    class Meta:
        model = PurchaseOrderModel
        filter_fields = {
            'po_date': ['exact'],
            'po_title': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)


class PurchaseOrderQuery(graphene.ObjectType):
    all_purchase_order = DjangoFilterConnectionField(
        PurchaseOrderNode, slug_name=graphene.String(required=True))

    def resolve_all_purchase_order(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return PurchaseOrderModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).order_by('-po_date')

        else:
            return PurchaseOrderModel.objects.none()
