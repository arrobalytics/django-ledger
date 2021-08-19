from django.db.models import Sum
from django.views.generic import ListView

from django_ledger.views.mixins import LoginRequiredMixIn
from django_ledger.models.items import ItemModel, ItemThroughModel


class InventoryListView(LoginRequiredMixIn, ListView):

    template_name = 'django_ledger/inventory_list.html'
    context_object_name = 'inventory_list'

    def get_queryset(self):
        return ItemThroughModel.objects.inventory_received(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).values('item_model__name', 'item_model__uom__name').annotate(
            total_quantity=Sum('quantity'), total_value=Sum('total_amount')
        )
