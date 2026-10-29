"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from typing import Optional

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView

from django_ledger.models import EntityModel
from django_ledger.models.entity import EntityModelQuerySet
from django_ledger.models.items import ItemTransactionModel, ItemTransactionModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class InventoryModelModelBaseViewMixIn(DjangoLedgerSecurityMixIn):
    """
    Shared inventory access scoped to the authorized business.
    """
    queryset: Optional[ItemTransactionModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = ItemTransactionModel.objects.inventory_pipeline_aggregate(
                entity_model=self.get_authorized_entity_instance()
            )
        return self.queryset


class InventoryListView(InventoryModelModelBaseViewMixIn, ListView):
    """
    Shows inventory that is ordered, in transit, or on hand.
    """
    template_name = 'django_ledger/inventory/inventory_list.html'
    context_object_name = 'inventory_list'
    http_method_names = ['get']

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        context['qs_count'] = qs.count()
        context['inventory_ordered'] = qs.is_ordered()
        context['inventory_in_transit'] = qs.in_transit()
        context['inventory_received'] = qs.is_received()

        context['page_title'] = _('Inventory')
        context['header_title'] = _('Inventory Status')
        context['header_subtitle'] = _('Ordered/In Transit/On Hand')
        context['header_subtitle_icon'] = 'ic:round-inventory'
        return context


class InventoryRecountView(DjangoLedgerSecurityMixIn, DetailView):
    """
    Compares counted inventory to recorded levels and posts adjustments
    so on-hand quantities match what was actually counted.
    """
    template_name = 'django_ledger/inventory/inventory_recount.html'
    http_method_names = ['get', 'post']
    slug_url_kwarg = 'entity_slug'
    queryset: Optional[EntityModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = self.get_authorized_entity_queryset()
        return self.queryset

    def counted_inventory(self):
        return ItemTransactionModel.objects.inventory_count(
            entity_model=self.AUTHORIZED_ENTITY_MODEL
        )

    def recorded_inventory(self, queryset=None, as_values=True):
        entity_model: EntityModel = self.AUTHORIZED_ENTITY_MODEL
        return entity_model.recorded_inventory(item_qs=queryset)

    def get_context_data(self, adjustment=None, counted_qs=None, recorded_qs=None, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Inventory Recount')
        context['header_title'] = _('Inventory Recount')

        recorded_qs = self.recorded_inventory() if not recorded_qs else recorded_qs
        counted_qs = self.counted_inventory() if not counted_qs else counted_qs
        adjustment = (
            EntityModel.inventory_adjustment(counted_qs, recorded_qs)
            if not adjustment
            else adjustment
        )

        context['count_inventory_received'] = counted_qs
        context['current_inventory_levels'] = recorded_qs
        context['inventory_adjustment'] = [
            (k, v) for k, v in adjustment.items() if any(v.values())
        ]
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.update_inventory()
        messages.add_message(
            request,
            level=messages.INFO,
            message=_('Successfully updated recorded inventory.'),
            extra_tags='is-success',
        )
        return HttpResponseRedirect(
            redirect_to=reverse(
                'django_ledger:inventory-recount',
                kwargs={'entity_slug': self.kwargs['entity_slug']},
            )
        )

    def update_inventory(self):
        entity_model: EntityModel = self.get_object()
        adj, counted_qs, recorded_qs = entity_model.update_inventory(commit=True)
        return adj, counted_qs, recorded_qs
