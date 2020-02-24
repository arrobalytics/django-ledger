from django.urls import reverse
from django.views.generic import ListView, UpdateView

from django_ledger.forms.invoice import InvoiceModelForm
from django_ledger.models.invoice import InvoiceModel


class InvoiceModelListView(ListView):
    template_name = 'django_ledger/invoice_list.html'
    context_object_name = 'invoices'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = 'Invoice List'
        return context

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return InvoiceModel.objects.on_entity(entity=entity_slug)


class InvoiceModelUpdateView(UpdateView):
    slug_url_kwarg = 'invoice_slug'
    slug_field = 'invoice_number'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice_update.html'
    form_class = InvoiceModelForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        context['page_title'] = f'Invoice {invoice}'
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_slug = self.kwargs['invoice_slug']
        return reverse('django_ledger:invoice-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_slug': invoice_slug
                       })

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return InvoiceModel.objects.on_entity(entity=entity_slug)
