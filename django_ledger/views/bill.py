from django.urls import reverse
from django.views.generic import ListView, UpdateView, CreateView

from django_ledger.abstracts.bill import generate_bill_number
from django_ledger.forms.bill import BillModelCreateForm, BillModelUpdateForm
from django_ledger.models import BillModel, LedgerModel, EntityModel


class BillModelListView(ListView):
    template_name = 'django_ledger/bill_list.html'
    context_object_name = 'bills'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = 'Bill List'
        context['header_title'] = 'Bill List'
        return context

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return BillModel.objects.on_entity(entity=entity_slug)


class BillModelCreateView(CreateView):
    template_name = 'django_ledger/bill_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Bill'
        context['header_title'] = 'Create Bill'
        return context

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = BillModelCreateForm(entity_slug=entity_slug,
                                   user_model=self.request.user,
                                   **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        bill = form.instance
        bill.bill_number = generate_bill_number()
        entity_slug = self.kwargs.get('entity_slug')
        entity_model = EntityModel.objects.for_user(
            user_model=self.request.user).get(slug__exact=entity_slug)
        ledger_model = LedgerModel.objects.create(
            entity=entity_model,
            posted=True,
            name=f'Bill {bill.bill_number}'
        )
        ledger_model.clean()
        bill.ledger = ledger_model
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class BillModelUpdateView(UpdateView):
    slug_url_kwarg = 'bill_slug'
    slug_field = 'bill_number'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_update.html'

    def get_form(self, form_class=None):
        return BillModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.bill_number
        title = f'Bill {invoice}'
        context['page_title'] = title
        context['header_title'] = title
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        bill_slug = self.kwargs['bill_slug']
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_slug': bill_slug
                       })

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        qs = BillModel.objects.for_user(
            user_model=self.request.user).filter(
            ledger__entity__slug__exact=entity_slug
        )
        return qs
