from django.urls import reverse
from django.views.generic import ListView, UpdateView, CreateView
from django.utils.translation import gettext_lazy as _

from django_ledger.forms.bill import BillModelCreateForm, BillModelUpdateForm
from django_ledger.models.bill import BillModel
from django_ledger.models.utils import new_bill_protocol


class BillModelListView(ListView):
    template_name = 'django_ledger/bill_list.html'
    context_object_name = 'bills'
    PAGE_TITLE = _('Bill List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return BillModel.objects.on_entity(entity=entity_slug)


class BillModelCreateView(CreateView):
    template_name = 'django_ledger/bill_create.html'
    PAGE_TITLE = _('Create Bill')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = BillModelCreateForm(entity_slug=entity_slug,
                                   user_model=self.request.user,
                                   **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        form.instance = new_bill_protocol(bill_model=form.instance,
                                          entity_slug=self.kwargs['entity_slug'],
                                          user_model=self.request.user)
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
        ).select_related('ledger')
        return qs
