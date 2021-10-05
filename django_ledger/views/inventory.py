from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView

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


def inventory_adjustment(counted_qs, recorded_qs) -> defaultdict:
    counted_map = {
        (i['item_model_id'], i['item_model__name'], i['item_model__uom__name']): {
            'count': i['total_quantity'],
            'value': i['total_value'],
            'avg_cost': i['total_value'] / Decimal.from_float(i['total_quantity'])
            if i['total_quantity'] else Decimal('0.00')
        } for i in counted_qs
    }
    recorded_map = {
        (i['uuid'], i['name'], i['uom__name']): {
            'count': i['inventory_received'] or Decimal.from_float(0.0),
            'value': i['inventory_received_value'] or Decimal.from_float(0.0),
            'avg_cost': i['inventory_received_value'] / i['inventory_received']
            if i['inventory_received'] else Decimal('0.00')
        } for i in recorded_qs
    }
    item_ids = list(set(list(counted_map.keys()) + list(recorded_map)))
    adjustment = defaultdict(lambda: {
        # keeps track of inventory recounts...
        'counted': Decimal('0.000'),
        'counted_value': Decimal('0.00'),
        'counted_avg_cost': Decimal('0.00'),

        # keeps track of inventory level...
        'recorded': Decimal('0.000'),
        'recorded_value': Decimal('0.00'),
        'recorded_avg_cost': Decimal('0.00'),

        # keeps track of necessary inventory adjustment...
        'count_diff': Decimal('0.000'),
        'value_diff': Decimal('0.00'),
        'avg_cost_diff': Decimal('0.00')
    })

    for uid in item_ids:
        data = counted_map.get(uid)
        if data:
            counted = Decimal.from_float(data['count'])
            avg_cost = data['value'] / counted if data['count'] else Decimal('0.000')

            adjustment[uid]['counted'] = counted
            adjustment[uid]['counted_value'] = data['value']
            adjustment[uid]['counted_avg_cost'] = avg_cost

            adjustment[uid]['count_diff'] += counted
            adjustment[uid]['value_diff'] += data['value']
            adjustment[uid]['avg_cost_diff'] += avg_cost

        data = recorded_map.get(uid)
        if data:
            counted = data['count']
            avg_cost = data['value'] / counted if data['count'] else Decimal('0.000')

            adjustment[uid]['recorded'] = counted
            adjustment[uid]['recorded_value'] = data['value']
            adjustment[uid]['recorded_avg_cost'] = avg_cost

            adjustment[uid]['count_diff'] -= counted
            adjustment[uid]['value_diff'] -= data['value']
            adjustment[uid]['avg_cost_diff'] -= avg_cost

    return adjustment


class InventoryRecountView(LoginRequiredMixIn, TemplateView):
    template_name = 'django_ledger/inventory_recount.html'
    http_method_names = ['get']

    def counted_inventory(self):
        entity_slug = self.kwargs['entity_slug']
        user_model = self.request.user
        return ItemThroughModel.objects.inventory_received_value(
            entity_slug=entity_slug,
            user_model=user_model
        ).values('item_model_id', 'item_model__name', 'item_model__uom__name', 'total_quantity', 'total_value')

    def recorded_inventory(self, queryset=None, as_values=True):
        entity_slug = self.kwargs['entity_slug']
        user_model = self.request.user
        if not queryset:
            recorded_qs = ItemModel.objects.inventory(
                entity_slug=entity_slug,
                user_model=user_model
            ).select_related('uom')
        else:
            recorded_qs = queryset
        if as_values:
            return recorded_qs.values(
                'uuid', 'name', 'uom__name', 'inventory_received', 'inventory_received_value')
        return recorded_qs

    def get_context_data(self, adjustment=None, counted_qs=None, recorded_qs=None, **kwargs):
        context = super(InventoryRecountView, self).get_context_data(**kwargs)
        context['page_title'] = _('Inventory Recount')
        context['header_title'] = _('Inventory Recount')

        recorded_qs = self.recorded_inventory() if not recorded_qs else recorded_qs
        counted_qs = self.counted_inventory() if not counted_qs else counted_qs
        adjustment = inventory_adjustment(counted_qs, recorded_qs) if not adjustment else adjustment

        context['count_inventory_received'] = counted_qs
        context['current_inventory_levels'] = recorded_qs
        context['inventory_adjustment'] = [(k, v) for k, v in adjustment.items() if any(v.values())]

        return context

    def get(self, request, *args, **kwargs):

        confirm = self.request.GET.get('confirm')
        # counted_qs = None
        # recorded_qs = None
        # adj = None

        if confirm:
            try:
                confirm = int(confirm)
            except TypeError:
                return HttpResponseBadRequest('Not Found. Invalid conform code...')
            finally:
                if confirm not in [0, 1]:
                    return HttpResponseNotFound('Not Found. Invalid conform code...')

            self.update_inventory()
            messages.add_message(
                request,
                level=messages.INFO,
                message=f'Successfully updated recorded inventory.',
                extra_tags='is-success'
            )
            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:inventory-recount',
                                    kwargs={
                                        'entity_slug': self.kwargs['entity_slug']
                                    })
            )
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def update_inventory(self):
        counted_qs = self.counted_inventory()
        recorded_qs = self.recorded_inventory(as_values=False)
        list(recorded_qs)
        recorded_qs_values = self.recorded_inventory(queryset=recorded_qs, as_values=True)
        adj = inventory_adjustment(counted_qs, recorded_qs_values)
        updated_items = list()
        for (uuid, name, uom), i in adj.items():
            item_model: ItemModel = recorded_qs.get(uuid__exact=uuid)
            item_model.inventory_received = i['counted']
            item_model.inventory_received_value = i['counted_value']
            updated_items.append(item_model)
        ItemModel.objects.bulk_update(updated_items,
                                      fields=[
                                          'inventory_received',
                                          'inventory_received_value',
                                          'updated'
                                      ])
        return adj, counted_qs, recorded_qs
