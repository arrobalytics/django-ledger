"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import (CreateView, ArchiveIndexView, YearArchiveView, MonthArchiveView, DetailView,
                                  UpdateView, DeleteView)

from django_ledger.forms.purchase_order import PurchaseOrderModelCreateForm, PurchaseOrderModelUpdateForm, \
    get_po_item_formset
from django_ledger.models import PurchaseOrderModel, ItemThroughModel
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
            'for_inventory': False,
            'po_date': localdate()
        }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = PurchaseOrderModelCreateForm(entity_slug=entity_slug,
                                            user_model=self.request.user,
                                            **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        po_model = new_po_protocol(
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
    update_items = False
    create_bills = False

    def post(self, request, entity_slug, *args, **kwargs):
        self.object = self.get_object()
        po_model: PurchaseOrderModel = self.object
        if self.update_items:
            PurchaseOrderItemFormset = get_po_item_formset(po_model)
            po_item_formset: PurchaseOrderItemFormset = PurchaseOrderItemFormset(request.POST,
                                                                                 user_model=self.request.user,
                                                                                 po_model=po_model,
                                                                                 entity_slug=entity_slug)

            context = self.get_context_data(item_formset=po_item_formset)

            if po_item_formset.is_valid():
                if po_item_formset.has_changed():
                    po_items = po_item_formset.save(commit=False)
                    all_received = all([
                        i['po_item_status'] == ItemThroughModel.STATUS_RECEIVED
                        for i in po_item_formset.cleaned_data if i
                    ])

                    for f in po_item_formset.forms:
                        i: ItemThroughModel = f.instance
                        if i:
                            if all([
                                i.po_item_status in [
                                    ItemThroughModel.STATUS_RECEIVED,
                                    ItemThroughModel.STATUS_IN_TRANSIT
                                ],
                                i.bill_model is None
                            ]):
                                messages.add_message(
                                    request=self.request,
                                    level=messages.ERROR,
                                    message=f'Item {i.item_model.__str__()} must be billed'
                                            f' before {i.get_po_item_status_display()}...',
                                    extra_tags='is-danger')
                                return self.render_to_response(context)

                    if all_received and po_model.fulfillment_date:

                        all_bills_paid = all([
                            f.instance.bill_model.paid_date for f in po_item_formset.forms
                        ])

                        if not all_bills_paid:
                            messages.add_message(
                                request=self.request,
                                level=messages.ERROR,
                                message=f'All Bills must be paid before PO being fulfilled..',
                                extra_tags='is-danger')
                            return self.render_to_response(context)

                    elif all_received and not po_model.fulfillment_date:
                        po_model.fulfillment_date = localdate()
                        po_model.fulfilled = True
                        po_model.clean()
                        po_model.save(update_fields=[
                            'fulfillment_date',
                            'fulfilled',
                            'updated'
                        ])

                    create_bill_uuids = [
                        str(i['uuid'].uuid) for i in po_item_formset.cleaned_data if i and i['create_bill'] is True
                    ]

                    if create_bill_uuids:
                        item_uuids = ','.join(create_bill_uuids)
                        redirect_url = reverse(
                            'django_ledger:bill-create-po',
                            kwargs={
                                'entity_slug': self.kwargs['entity_slug'],
                                'po_pk': po_model.uuid,
                            }
                        )
                        redirect_url += f'?item_uuids={item_uuids}'
                        return HttpResponseRedirect(redirect_url)

                    for item in po_items:
                        if not item.po_model:
                            item.po_model = po_model
                    po_item_formset.save()
                    po_model.update_po_state()
                    po_model.clean()
                    po_model.save(update_fields=['po_amount',
                                                 'po_amount_received',
                                                 'updated'])

            else:
                return self.render_to_response(context)
        return super().post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        return PurchaseOrderModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_form_kwargs(self):
        if self.update_items:
            return {
                'initial': self.get_initial(),
                'prefix': self.get_prefix(),
                'instance': self.object
            }
        return super(PurchaseOrderModelUpdateView, self).get_form_kwargs()

    def get_context_data(self, *, object_list=None, item_formset=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        po_model: PurchaseOrderModel = self.object
        title = f'Purchase Order {po_model.po_number}'
        context['page_title'] = title
        context['header_title'] = title
        if not item_formset:
            po_item_queryset, item_data = po_model.get_po_item_data(
                queryset=po_model.itemthroughmodel_set.select_related('bill_model', 'po_model').order_by(
                    'created'
                )
            )
            PurchaseOrderItemFormset = get_po_item_formset(po_model)
            context['item_formset'] = PurchaseOrderItemFormset(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                po_model=po_model,
                queryset=po_item_queryset,
            )
            context['total_amount_due'] = item_data['amount_due']
            context['total_paid'] = item_data['total_paid']
        else:
            context['item_formset'] = item_formset
            context['total_amount_due'] = po_model.po_amount
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        po_pk = self.kwargs['po_pk']
        return reverse('django_ledger:po-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'po_pk': po_pk
                       })

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('entity')

    def form_valid(self, form: PurchaseOrderModelUpdateForm):
        po_model: PurchaseOrderModel = form.save(commit=False)

        if form.has_changed():
            po_items_qs = ItemThroughModel.objects.for_po(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                po_pk=po_model.uuid,
            ).select_related('bill_model')

            if all(['po_status' in form.changed_data,
                    po_model.po_status == po_model.PO_STATUS_APPROVED]):
                po_items_qs.update(po_item_status=ItemThroughModel.STATUS_NOT_ORDERED)

            if 'fulfilled' in form.changed_data:

                if not all([i.bill_model for i in po_items_qs]):
                    messages.add_message(self.request,
                                         messages.ERROR,
                                         f'All PO items must be billed before marking'
                                         f' PO: {po_model.po_number} as fulfilled.',
                                         extra_tags='is-danger')
                    return self.get(self.request)

                else:
                    if not all([i.bill_model.paid for i in po_items_qs]):
                        messages.add_message(self.request,
                                             messages.SUCCESS,
                                             f'All bills must be paid before marking'
                                             f' PO: {po_model.po_number} as fulfilled.',
                                             extra_tags='is-success')
                        return self.get(self.request)

                po_items_qs.update(po_item_status=ItemThroughModel.STATUS_RECEIVED)

        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'{self.object.po_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)


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
            queryset=po_model.itemthroughmodel_set.all().select_related('item_model')
        )
        context['po_items'] = po_items_qs
        context['po_total_amount'] = sum(
            i['po_total_amount'] for i in po_items_qs.values(
                'po_total_amount', 'po_item_status') if i['po_item_status'] != 'cancelled')
        return context

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class PurchaseOrderModelDeleteView(LoginRequiredMixIn, DeleteView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/po_delete.html'
    extra_context = {
        'hide_menu': True,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        po_model: PurchaseOrderModel = self.object
        context['page_title'] = _('Delete Purchase Order ') + po_model.po_number
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        return PurchaseOrderModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                       })

    def delete(self, request, *args, **kwargs):
        po_model: PurchaseOrderModel = self.get_object()
        self.object = po_model
        po_items_qs = po_model.itemthroughmodel_set.filter(bill_model__isnull=False)
        if po_items_qs.exists():
            messages.add_message(request,
                                 message=f'Cannot delete {po_model.po_number} because it has related bills.',
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
            url = reverse('django_ledger:po-update',
                          kwargs={
                              'entity_slug': self.kwargs['entity_slug'],
                              'po_pk': self.kwargs['po_pk']
                          })
            return HttpResponseRedirect(url)
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)

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
