"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (CreateView, ArchiveIndexView, YearArchiveView, MonthArchiveView, DetailView,
                                  UpdateView)

from django_ledger.forms.purchase_order import PurchaseOrderModelCreateForm, PurchaseOrderModelUpdateForm, \
    PurchaseOrderItemFormset
from django_ledger.models import PurchaseOrderModel
from django_ledger.utils import new_po_protocol
from django_ledger.views.mixins import LoginRequiredMixIn


class PurchaseOrderModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/po_list.html'
    context_object_name = 'po_list'
    PAGE_TITLE = _('PO List')
    date_field = 'po_date'
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).order_by('-po_date')

    def get_allow_future(self):
        allow_future = self.request.GET.get('allow_future')
        if allow_future:
            try:
                allow_future = int(allow_future)
                if allow_future in (0, 1):
                    return bool(allow_future)
            except ValueError:
                pass
        return False


class PurchaseOrderModelYearListView(YearArchiveView, PurchaseOrderModelListView):
    paginate_by = 10
    make_object_list = True


class PurchaseOrderModelMonthListView(MonthArchiveView, PurchaseOrderModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class PurchaseOrderModelCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/po_create.html'
    PAGE_TITLE = _('Create Purchase Order')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_initial(self):
        return {
            'for_inventory': False
        }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = PurchaseOrderModelCreateForm(entity_slug=entity_slug,
                                            user_model=self.request.user,
                                            **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        ledger_model, po_model = new_po_protocol(
            po_model=form.instance,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )
        form.instance = po_model
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:po-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class PurchaseOrderModelUpdateView(LoginRequiredMixIn, UpdateView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/po_update.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill'
    }

    def get_form(self, form_class=None):
        return PurchaseOrderModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        po_number = self.object.po_number
        title = f'Purchase Order {po_number}'
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

        po_model: PurchaseOrderModel = self.object
        po_item_queryset, item_data = po_model.get_po_item_data(
            queryset=po_model.purchaseorderitemthroughmodel_set.all()
        )
        context['item_formset'] = PurchaseOrderItemFormset(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            po_pk=self.object.uuid,
            queryset=po_item_queryset
        )
        context['total_amount_due'] = item_data['amount_due']
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        po_pk = self.kwargs['po_pk']
        return reverse('django_ledger:po-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'po_pk': po_pk
                       })

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'purchaseorderitemthroughmodel_set'
        ).select_related('ledger', 'vendor')

    # def form_valid(self, form):
    #     form.save(commit=False)
    #     messages.add_message(self.request,
    #                          messages.SUCCESS,
    #                          f'Bill {self.object.bill_number} successfully updated.',
    #                          extra_tags='is-success')
    #     return super().form_valid(form)
#
#
# class BillModelItemsUpdateView(LoginRequiredMixIn, View):
#     http_method_names = ['post']
#
#     def post(self, request, entity_slug, bill_pk, **kwargs):
#         bill_item_formset: BillItemFormset = BillItemFormset(request.POST,
#                                                              user_model=self.request.user,
#                                                              bill_pk=bill_pk,
#                                                              entity_slug=entity_slug)
#
#         if bill_item_formset.is_valid():
#             invoice_items = bill_item_formset.save(commit=False)
#
#             if bill_item_formset.has_changed():
#                 bill_qs = BillModel.objects.for_entity(
#                     user_model=self.request.user,
#                     entity_slug=entity_slug
#                 )
#                 bill_model: BillModel = get_object_or_404(bill_qs, uuid__exact=bill_pk)
#
#                 entity_qs = EntityModel.objects.for_user(
#                     user_model=self.request.user
#                 )
#                 entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
#
#                 for item in invoice_items:
#                     item.entity = entity_model
#                     item.bill_model = bill_model
#
#                 bill_item_list = bill_item_formset.save()
#                 bill_model.update_amount_due()
#                 bill_model.new_state(commit=True)
#                 bill_model.clean()
#                 bill_model.save(update_fields=['amount_due',
#                                                'amount_receivable',
#                                                'amount_unearned',
#                                                'amount_earned',
#                                                'updated'])
#
#                 bill_model.migrate_state(
#                     entity_slug=entity_slug,
#                     user_model=self.request.user,
#                     item_models=bill_item_list,
#                     force_migrate=True
#                 )
#
#         return HttpResponseRedirect(reverse('django_ledger:bill-update',
#                                             kwargs={
#                                                 'entity_slug': entity_slug,
#                                                 'bill_pk': bill_pk
#                                             }))
#
#
class PurchaseOrderModelDetailView(LoginRequiredMixIn, DetailView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/po_detail.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill',
        'hide_menu': True
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        po_model: PurchaseOrderModel = self.object
        title = f'Purchase Order {po_model.po_number}'
        context['page_title'] = title
        context['header_title'] = title

        po_model: PurchaseOrderModel = self.object
        po_items_qs, item_data = po_model.get_po_item_data(
            queryset=po_model.purchaseorderitemthroughmodel_set.all()
        )
        context['po_items'] = po_items_qs
        context['total_amount_due'] = item_data['amount_due']
        return context

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
#
#
# class BillModelDeleteView(LoginRequiredMixIn, DeleteView):
#     slug_url_kwarg = 'bill_pk'
#     slug_field = 'uuid'
#     context_object_name = 'bill'
#     template_name = 'django_ledger/bill_delete.html'
#     extra_context = {
#         'hide_menu': True,
#         'header_subtitle_icon': 'uil:bill'
#     }
#
#     def get_context_data(self, *, object_list=None, **kwargs):
#         context = super().get_context_data(object_list=object_list, **kwargs)
#         context['page_title'] = _('Delete Bill ') + self.object.bill_number
#         context['header_title'] = context['page_title']
#         return context
#
#     def get_queryset(self):
#         return BillModel.objects.for_entity(
#             entity_slug=self.kwargs['entity_slug'],
#             user_model=self.request.user
#         )
#
#     def get_success_url(self):
#         return reverse('django_ledger:entity-dashboard',
#                        kwargs={
#                            'entity_slug': self.kwargs['entity_slug'],
#                        })
#
#
# class BillModelMarkPaidView(LoginRequiredMixIn,
#                             View,
#                             SingleObjectMixin):
#     http_method_names = ['post']
#     slug_url_kwarg = 'bill_pk'
#     slug_field = 'uuid'
#
#     def get_queryset(self):
#         return BillModel.objects.for_entity(
#             entity_slug=self.kwargs['entity_slug'],
#             user_model=self.request.user
#         ).select_related('ledger')
#
#     def post(self, request, *args, **kwargs):
#         bill: BillModel = self.get_object()
#         mark_accruable_paid(
#             accruable_model=bill,
#             entity_slug=self.kwargs['entity_slug'],
#             user_model=self.request.user
#         )
#         messages.add_message(request,
#                              messages.SUCCESS,
#                              f'Successfully marked bill {bill.bill_number} as Paid.',
#                              extra_tags='is-success')
#         redirect_url = reverse('django_ledger:bill-detail',
#                                kwargs={
#                                    'entity_slug': self.kwargs['entity_slug'],
#                                    'bill_pk': bill.uuid
#                                })
#         return HttpResponseRedirect(redirect_url)
