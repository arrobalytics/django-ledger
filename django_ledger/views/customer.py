"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Customer views grouped by CRUD.

  * CREATE   — CustomerModelCreateView
  * RETRIEVE — CustomerModelListView, CustomerModelDetailView
  * UPDATE   — CustomerModelUpdateView
  * DELETE   — CustomerModelDeleteView (stub)

Querysets are entity-scoped via CustomerModelModelBaseView after
DjangoLedgerSecurityMixIn authorizes the entity slug.
"""

from typing import Optional

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from django_ledger.forms.customer import CustomerModelForm
from django_ledger.models.customer import CustomerModel, CustomerModelQueryset
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class CustomerModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped customer queryset shared by all customer CRUD views."""

    queryset: Optional[CustomerModelQueryset] = None

    def get_queryset(self) -> CustomerModelQueryset:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: CustomerModelQueryset = CustomerModel.objects.for_entity(
                entity_model=entity_model,
            ).order_by('-updated')
            self.queryset = qs
        return self.queryset


# -----------------
# RETRIEVE (List)
# -----------------
class CustomerModelListView(CustomerModelModelBaseView, ListView):
    """Lists customers belonging to the authorized entity."""

    template_name = 'django_ledger/customer/customer_list.html'
    PAGE_TITLE = _('Customer List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'dashicons:businesswoman',
    }
    context_object_name = 'customer_list'


# -----------------
# CREATE
# -----------------
class CustomerModelCreateView(CustomerModelModelBaseView, CreateView):
    """Creates a customer bound to the authorized entity."""

    template_name = 'django_ledger/customer/customer_create.html'
    PAGE_TITLE = _('Create New Customer')
    form_class = CustomerModelForm
    context_object_name = 'customer'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'dashicons:businesswoman',
    }

    def get_success_url(self):
        return reverse(
            'django_ledger:customer-list',
            kwargs={'entity_slug': self.kwargs['entity_slug']},
        )

    def form_valid(self, form):
        customer_model: CustomerModel = form.save(commit=False)
        # Reuse the already-authorized entity — do not re-query by slug alone.
        customer_model.entity_model = self.get_authorized_entity_instance()
        customer_model.save()
        return super().form_valid(form)


# -----------------
# UPDATE
# -----------------
class CustomerModelUpdateView(CustomerModelModelBaseView, UpdateView):
    """Updates an existing customer within the authorized entity."""

    template_name = 'django_ledger/customer/customer_update.html'
    PAGE_TITLE = _('Customer Update')
    form_class = CustomerModelForm
    context_object_name = 'customer'
    slug_url_kwarg = 'customer_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(CustomerModelUpdateView, self).get_context_data(**kwargs)
        customer_model: CustomerModel = self.object
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = customer_model.customer_number
        context['header_subtitle_icon'] = 'dashicons:businesswoman'
        return context

    def get_success_url(self):
        return reverse(
            'django_ledger:customer-list',
            kwargs={'entity_slug': self.kwargs['entity_slug']},
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


# -----------------
# DELETE
# -----------------
class CustomerModelDeleteView(CustomerModelModelBaseView, DeleteView):
    """Placeholder delete view (template/behavior not yet implemented)."""

    pass


# -----------------
# RETRIEVE (Detail)
# -----------------
class CustomerModelDetailView(CustomerModelModelBaseView, DetailView):
    """
    Customer profile with related receipts and invoices.

    Related querysets are constrained to the authorized entity to prevent
    cross-entity leakage of financial documents.
    """

    template_name = 'django_ledger/customer/customer_detail.html'
    context_object_name = 'customer'
    PAGE_TITLE = _('Customer Details')
    slug_url_kwarg = 'customer_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer: CustomerModel = self.object
        receipts_qs = (
            ReceiptModel.objects.for_entity(entity_model=self.AUTHORIZED_ENTITY_MODEL)
            .for_customer(customer_model=customer)
            .order_by('-updated')
        )
        invoices_qs = (
            InvoiceModel.objects.for_entity(entity_model=self.AUTHORIZED_ENTITY_MODEL)
            .filter(customer=customer)
            .order_by('-updated')
        )
        context.update(
            {
                'page_title': self.PAGE_TITLE,
                'header_title': self.PAGE_TITLE,
                'header_subtitle': f'{customer.customer_name} · {customer.customer_number}',
                'header_subtitle_icon': 'dashicons:businesswoman',
                'receipts': receipts_qs,
                'invoices': invoices_qs,
            }
        )
        return context
