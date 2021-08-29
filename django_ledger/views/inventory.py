from django.db.models import Sum
from django.views.generic import ListView

from django_ledger.views.mixins import LoginRequiredMixIn
from django_ledger.models.items import ItemModel, ItemThroughModel
from django.utils.translation import gettext_lazy as _


class InventoryListView(LoginRequiredMixIn, ListView):
    template_name = 'django_ledger/inventory_list.html'
    context_object_name = 'inventory_list'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(InventoryListView, self).get_context_data(**kwargs)
        qs = self.get_queryset()
        context['qs_count'] = qs.count()

        # ordered inventory...
        ordered_qs = qs.is_ordered()
        context['inventory_ordered'] = ordered_qs

        # in transit inventory...
        in_transit_qs = qs.in_transit()
        context['inventory_in_transit'] = in_transit_qs

        # on hand inventory...
        received_qs = qs.is_received()
        context['inventory_received'] = received_qs

        context['page_title'] = _('Inventory')
        context['header_title'] = _('Inventory Status')
        context['header_subtitle'] = _('Ordered/In Transit/On Hand')
        context['header_subtitle_icon'] = 'ic:round-inventory'
        return context

    def get_queryset(self):
        return ItemThroughModel.objects.inventory_all(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).values('item_model__name', 'item_model__uom__name', 'po_item_status').annotate(
            total_quantity=Sum('quantity'), total_value=Sum('total_amount')
        )
