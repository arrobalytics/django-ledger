from django.contrib import messages
from django.core.exceptions import FieldError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import UpdateView, CreateView, DeleteView, MonthArchiveView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.invoice import InvoiceModelUpdateForm, InvoiceModelCreateForm
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.utils import new_invoice_protocol, mark_progressible_paid


class InvoiceModelListView(MonthArchiveView):
    template_name = 'django_ledger/invoice_list.html'
    context_object_name = 'invoices'
    PAGE_TITLE = _('Invoice List')
    date_field = 'date'
    month_format = '%m'
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_year(self):
        year = self.request.GET.get('year')
        return year if year else localdate().year

    def get_month(self):
        month = self.request.GET.get('month')
        if not month:
            month = str(localdate().month)
            month = '0' + month if len(month) == 1 else month
        return month

    def get_queryset(self):
        qs = InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')
        sort = self.request.GET.get('sort')
        if sort:
            try:
                qs = qs.order_by(sort)
            except FieldError:
                messages.add_message(self.request,
                                     level=messages.ERROR,
                                     message=f'Invalid sort {sort}',
                                     extra_tags='is-danger')
        return qs


class InvoiceModelCreateView(CreateView):
    template_name = 'django_ledger/invoice_create.html'
    PAGE_TITLE = _('Create Invoice')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

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

        ledger_model = self.object.ledger

        if ledger_model.locked:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! This Invoice is Locked. Must unlock before making any changes.',
                                 extra_tags='is-danger')

        if not ledger_model.posted:
            messages.add_message(self.request,
                                 messages.INFO,
                                 f'This Invoice has not been posted. Must post to see ledger changes.',
                                 extra_tags='is-info')

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
        ).select_related('ledger', 'customer')

    def form_valid(self, form):
        form.save(commit=False)
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Invoice {self.object.invoice_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)


class InvoiceModelDeleteView(DeleteView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    template_name = 'django_ledger/invoice_delete.html'
    context_object_name = 'invoice'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Invoice ') + self.object.invoice_number
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class InvoiceModelMarkPaidView(View, SingleObjectMixin):
    http_method_names = ['post']
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def post(self, request, *args, **kwargs):
        invoice: InvoiceModel = self.get_object()
        mark_progressible_paid(
            progressible_model=invoice,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        messages.add_message(request,
                             messages.SUCCESS,
                             f'Successfully marked bill {invoice.invoice_number} as Paid.',
                             extra_tags='is-success')
        redirect_url = reverse('django_ledger:entity-dashboard',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug']
                               })
        return HttpResponseRedirect(redirect_url)
