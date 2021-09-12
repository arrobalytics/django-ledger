from collections import defaultdict
from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from django.http import HttpResponseBadRequest

from django_ledger.models.items import ItemThroughModel, ItemModel
from django_ledger.views.mixins import LoginRequiredMixIn


class InventoryListView(LoginRequiredMixIn, ListView):
    template_name = 'django_ledger/inventory_list.html'
    context_object_name = 'inventory_list'
    http_method_names = ['get']

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(InventoryListView, self).get_context_data(**kwargs)
        qs = self.get_queryset()

        # evaluates the queryset...
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
        return ItemThroughModel.objects.inventory_value(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class InventoryRecountView(LoginRequiredMixIn, TemplateView):
    template_name = 'django_ledger/inventory_recount.html'
    http_method_names = ['get']

    def counted_inventory(self):
        entity_slug = self.kwargs['entity_slug']
        user_model = self.request.user
        return ItemThroughModel.objects.inventory_received_value(
            entity_slug=entity_slug,
            user_model=user_model
        ).values('item_model_id', 'item_model__name', 'item_model__uom__name', 'quantity', 'total_amount')

    def recorded_inventory(self):
        entity_slug = self.kwargs['entity_slug']
        user_model = self.request.user
        return ItemModel.objects.inventory(
            entity_slug=entity_slug,
            user_model=user_model
        ).values('uuid', 'name', 'uom__name', 'inventory_received', 'inventory_received_value')

    def calculate_adjustment(self, counted, recorded):
        counted_map = {
            (i['item_model_id'], i['item_model__name'], i['item_model__uom__name']): {
                'count': i['quantity'],
                'value': i['total_amount']
            } for i in counted
        }
        recorded_map = {
            (i['uuid'], i['name'], i['uom__name']): {
                'count': i['inventory_received'] or 0,
                'value': i['inventory_received_value'] or 0
            } for i in recorded
        }
        item_ids = list(set(list(counted_map.keys()) + list(recorded_map)))

        adjustment = defaultdict(lambda: {
            'counted': 0,
            'value_counted': Decimal.from_float(0.00),
            'counted_avg_cost': Decimal.from_float(0.00),
            'recorded': 0,
            'recorded_value': Decimal.from_float(0.00),
            'count_diff': 0,
            'value_diff': Decimal.from_float(0.00)})

        for uid in item_ids:
            data = counted_map.get(uid)
            if data:
                adjustment[uid]['counted'] = data['count']
                adjustment[uid]['counted_value'] = data['value']
                adjustment[uid]['counted_avg_cost'] = data['value'] / Decimal.from_float(data['count'])
                adjustment[uid]['count_diff'] += data['count']
                adjustment[uid]['value_diff'] += data['value']

            data = recorded_map.get(uid)
            if data:
                adjustment[uid]['recorded'] = data['count']
                adjustment[uid]['recorded_value'] = data['value']
                adjustment[uid]['count_diff'] -= data['count']
                adjustment[uid]['value_diff'] -= data['value']

        return adjustment

    def get_context_data(self, **kwargs):
        context = super(InventoryRecountView, self).get_context_data(**kwargs)
        context['page_title'] = _('Inventory Recount')
        context['header_title'] = _('Inventory Recount')

        counted_inventory_qs = self.counted_inventory()
        recorded_inventory_qs = self.recorded_inventory()

        context['count_inventory_received'] = counted_inventory_qs
        context['current_inventory_levels'] = recorded_inventory_qs
        adjustment = self.calculate_adjustment(counted_inventory_qs, recorded_inventory_qs)
        context['inventory_diff'] = [(k, v) for k, v in adjustment.items() if any(v.values())]

        return context

    def get(self, request, *args, **kwargs):

        confirm = self.request.GET.get('confirm')

        if confirm:
            try:
                confirm = int(confirm)
            except TypeError:
                return HttpResponseBadRequest()
            finally:
                if confirm not in [0, 1]:
                    return HttpResponseBadRequest()

            confirm = bool(confirm)

            self.update_inventory()

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def update_inventory(self):
        pass
