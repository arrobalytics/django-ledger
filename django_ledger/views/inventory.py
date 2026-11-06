"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Inventory views (RETRIEVE + recount ACTION).

  * RETRIEVE — InventoryListView
  * ACTION   — InventoryRecountView (recounts on-hand quantities)

All item transactions are scoped through the authorized entity.
"""

from typing import Optional

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView

from django_ledger.models import EntityModel
from django_ledger.models.entity import EntityModelQuerySet
from django_ledger.models.items import ItemTransactionModel, ItemTransactionModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class InventoryItemTransactionModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Entity-scoped inventory pipeline queryset shared by inventory status views.
    """

    queryset: Optional[ItemTransactionModelQuerySet] = None

    def get_queryset(self) -> ItemTransactionModelQuerySet:
        if self.queryset is None:
            qs: ItemTransactionModelQuerySet = ItemTransactionModel.objects.inventory_pipeline_aggregate(
                entity_model=self.get_authorized_entity_instance()
            )
            self.queryset = qs
        return super().get_queryset()


class InventoryRecountModelBaseView(DjangoLedgerSecurityMixIn):
    """
    User-scoped entity queryset used by the inventory recount action view.
    """

    queryset: Optional[EntityModelQuerySet] = None

    def get_queryset(self) -> EntityModelQuerySet:
        if self.queryset is None:
            qs: EntityModelQuerySet = EntityModel.objects.for_user(user_model=self.request.user)
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE (List)
# -----------------
class InventoryListView(InventoryItemTransactionModelBaseView, ListView):
    """Lists inventory item transactions for the authorized entity."""

    template_name = 'django_ledger/inventory/inventory_list.html'
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


# -----------------
# ACTION (Recount)
# -----------------
class InventoryRecountView(InventoryRecountModelBaseView, DetailView):
    """Recounts on-hand inventory quantities for the authorized entity."""

    template_name = 'django_ledger/inventory/inventory_recount.html'
    http_method_names = ['get']
    slug_url_kwarg = 'entity_slug'

    def counted_inventory(self):
        return ItemTransactionModel.objects.inventory_count(entity_model=self.AUTHORIZED_ENTITY_MODEL)

    def recorded_inventory(self, queryset=None, as_values=True):
        entity_model: EntityModel = self.AUTHORIZED_ENTITY_MODEL
        recorded_qs = entity_model.recorded_inventory(item_qs=queryset)
        return recorded_qs

    def get_context_data(self, adjustment=None, counted_qs=None, recorded_qs=None, **kwargs):
        self.object = self.get_object()
        context = super(InventoryRecountView, self).get_context_data(**kwargs)
        context['page_title'] = _('Inventory Recount')
        context['header_title'] = _('Inventory Recount')

        recorded_qs = self.recorded_inventory() if not recorded_qs else recorded_qs
        counted_qs = self.counted_inventory() if not counted_qs else counted_qs
        adjustment = EntityModel.inventory_adjustment(counted_qs, recorded_qs) if not adjustment else adjustment

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

            if confirm not in [0, 1]:
                return HttpResponseNotFound('Not Found. Invalid conform code...')

            self.update_inventory()
            messages.add_message(
                request,
                level=messages.INFO,
                message=f'Successfully updated recorded inventory.',
                extra_tags='is-success',
            )
            return HttpResponseRedirect(
                redirect_to=reverse(
                    'django_ledger:inventory-recount',
                    kwargs={'entity_slug': self.kwargs['entity_slug']},
                )
            )
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def update_inventory(self):
        entity_model: EntityModel = self.get_object()
        adj, counted_qs, recorded_qs = entity_model.update_inventory(commit=True)
        return adj, counted_qs, recorded_qs
