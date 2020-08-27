from django.urls import reverse
from django.views.generic import ListView, UpdateView, CreateView

from django_ledger.forms.invoice import InvoiceModelUpdateForm, InvoiceModelCreateForm
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.utils import new_invoice_protocol


class InvoiceModelListView(ListView):
    template_name = 'django_ledger/invoice_list.html'
    context_object_name = 'invoices'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = 'Invoice List'
        context['header_title'] = 'Invoice List'
        return context

    def get_queryset(self):
        entity_slug = self.kwargs['entity_slug']
        return InvoiceModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=entity_slug
        )


class InvoiceModelCreateView(CreateView):
    template_name = 'django_ledger/invoice_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Invoice'
        context['header_title'] = 'Create Invoice'
        return context

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = InvoiceModelCreateForm(
            entity_slug=entity_slug,
            user_model=self.request.user,
            **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        form.instance = new_invoice_protocol(
            invoice_model=form.instance,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class InvoiceModelUpdateView(UpdateView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice_update.html'
    form_class = InvoiceModelUpdateForm

    def get_form(self, form_class=None):
        return InvoiceModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        title = f'Invoice {invoice}'
        context['page_title'] = title
        context['header_title'] = title
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_pk = self.kwargs['invoice_pk']
        return reverse('django_ledger:invoice-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': invoice_pk
                       })

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')
