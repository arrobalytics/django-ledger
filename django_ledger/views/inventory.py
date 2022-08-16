from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView

from django_ledger.models import EntityModel, inventory_adjustment
from django_ledger.models.items import ItemTransactionModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class InventoryListView(DjangoLedgerSecurityMixIn, ListView):
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
        return ItemTransactionModel.objects.inventory_pipeline_aggregate(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class InventoryRecountView(DjangoLedgerSecurityMixIn, DetailView):
    template_name = 'django_ledger/inventory_recount.html'
    http_method_names = ['get']
    slug_url_kwarg = 'entity_slug'

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user
        )

    def counted_inventory(self):
        entity_slug = self.kwargs['entity_slug']
        user_model = self.request.user
        return ItemTransactionModel.objects.inventory_count(
            entity_slug=entity_slug,
            user_model=user_model
        )

    def recorded_inventory(self, queryset=None, as_values=True):
        entity_model: EntityModel = self.get_object()
        user_model = self.request.user
        recorded_qs = entity_model.recorded_inventory(
            user_model=user_model,
            queryset=queryset
        )
        return recorded_qs

    def get_context_data(self, adjustment=None, counted_qs=None, recorded_qs=None, **kwargs):
        self.object = self.get_object()
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
        entity_model: EntityModel = self.get_object()
        adj, counted_qs, recorded_qs = entity_model.update_inventory(
            user_model=self.request.user,
            commit=True)
        return adj, counted_qs, recorded_qs
