from django.urls import reverse
from django.views.generic import ListView, UpdateView, CreateView

from django_ledger.abstracts.invoice import generate_invoice_number
from django_ledger.forms.invoice import InvoiceModelUpdateForm, InvoiceModelCreateForm
from django_ledger.models import InvoiceModel, LedgerModel, EntityModel


class InvoiceModelListView(ListView):
    template_name = 'django_ledger/invoice_list.html'
    context_object_name = 'invoices'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = 'Invoice List'
        context['header_title'] = 'Invoice List'
        return context

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return InvoiceModel.objects.on_entity(entity=entity_slug)


class InvoiceModelCreateView(CreateView):
    form_class = InvoiceModelCreateForm
    template_name = 'django_ledger/invoice_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Invoice'
        context['header_title'] = 'Create Invoice'
        return context

    def form_valid(self, form):
        invoice = form.instance
        invoice.invoice_number = generate_invoice_number()
        entity_slug = self.kwargs.get('entity_slug')
        entity_model = EntityModel.objects.for_user(user=self.request.user).get(slug__exact=entity_slug)
        ledger_model = LedgerModel.objects.create(
            entity=entity_model,
            name=f'Invoice {invoice.invoice_number}'
        )
        ledger_model.clean()
        invoice.ledger = ledger_model
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class InvoiceModelUpdateView(UpdateView):
    slug_url_kwarg = 'invoice_slug'
    slug_field = 'invoice_number'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice_update.html'
    form_class = InvoiceModelUpdateForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        title = f'Invoice {invoice}'
        context['page_title'] = title
        context['header_title'] = title
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
        qs = InvoiceModel.objects.for_user(user_model=self.request.user).filter(
            ledger__entity__slug__exact=entity_slug
        )
        return qs
