"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (CreateView, ArchiveIndexView, YearArchiveView, MonthArchiveView, DetailView,
                                  UpdateView, DeleteView, RedirectView)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.purchase_order import (PurchaseOrderModelCreateForm, BasePurchaseOrderModelUpdateForm,
                                                DraftPurchaseOrderModelUpdateForm, ReviewPurchaseOrderModelUpdateForm,
                                                ApprovedPurchaseOrderModelUpdateForm,
                                                get_po_itemtxs_formset_class)
from django_ledger.models import PurchaseOrderModel, ItemTransactionModel, EstimateModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class PurchaseOrderModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = PurchaseOrderModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity', 'ce_model')
        return super().get_queryset()


class PurchaseOrderModelListView(DjangoLedgerSecurityMixIn,
                                 PurchaseOrderModelModelViewQuerySetMixIn,
                                 ArchiveIndexView):
    template_name = 'django_ledger/purchase_order/po_list.html'
    context_object_name = 'po_list'
    PAGE_TITLE = _('PO List')
    date_field = 'created'
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

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


class PurchaseOrderModelYearListView(YearArchiveView,
                                     PurchaseOrderModelListView):
    paginate_by = 10
    make_object_list = True


class PurchaseOrderModelMonthListView(MonthArchiveView,
                                      PurchaseOrderModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class PurchaseOrderModelCreateView(DjangoLedgerSecurityMixIn,
                                   PurchaseOrderModelModelViewQuerySetMixIn,
                                   CreateView):
    template_name = 'django_ledger/purchase_order/po_create.html'
    PAGE_TITLE = _('Create Purchase Order')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }
    for_estimate = False

    def get(self, request, entity_slug, **kwargs):
        response = super(PurchaseOrderModelCreateView, self).get(request, entity_slug, **kwargs)
        if self.for_estimate and 'ce_pk' in self.kwargs:
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=entity_slug,
                user_model=self.request.user
            )
            estimate_model: EstimateModel = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            if not estimate_model.can_bind():
                return HttpResponseNotFound('404 Not Found')
        return response

    def get_context_data(self, **kwargs):
        context = super(PurchaseOrderModelCreateView, self).get_context_data(**kwargs)

        if self.for_estimate:
            context['form_action_url'] = reverse('django_ledger:po-create-estimate',
                                                 kwargs={
                                                     'entity_slug': self.kwargs['entity_slug'],
                                                     'ce_pk': self.kwargs['ce_pk']
                                                 })
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('customer')
            estimate_model = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            context['estimate_model'] = estimate_model

        else:
            context['form_action_url'] = reverse('django_ledger:po-create',
                                                 kwargs={
                                                     'entity_slug': self.kwargs['entity_slug']
                                                 })
        return context

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = PurchaseOrderModelCreateForm(entity_slug=entity_slug,
                                            user_model=self.request.user,
                                            **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        po_model: PurchaseOrderModel = form.save(commit=False)
        po_model = po_model.configure(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user)

        if self.for_estimate:
            ce_pk = self.kwargs['ce_pk']
            estimate_model_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            )
            estimate_model = get_object_or_404(estimate_model_qs, uuid__exact=ce_pk)
            po_model.action_bind_estimate(estimate_model=estimate_model, commit=False)
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']

        if self.for_estimate:
            ce_pk = self.kwargs['ce_pk']
            return reverse('django_ledger:customer-estimate-detail',
                           kwargs={
                               'entity_slug': self.kwargs['entity_slug'],
                               'ce_pk': ce_pk
                           })
        return reverse('django_ledger:po-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class PurchaseOrderModelUpdateView(DjangoLedgerSecurityMixIn,
                                   PurchaseOrderModelModelViewQuerySetMixIn,
                                   UpdateView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/purchase_order/po_update.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill'
    }
    action_update_items = False

    def get_context_data(self, itemtxs_formset=None, **kwargs):
        context = super().get_context_data(**kwargs)
        po_model: PurchaseOrderModel = self.object
        title = f'Purchase Order {po_model.po_number}'
        context['page_title'] = title
        context['header_title'] = title

        # continue here: pass item QS to item_form...
        if not itemtxs_formset:
            itemtxs_qs = self.get_po_itemtxs_qs(po_model)
            itemtxs_qs, itemtxs_agg = po_model.get_itemtxs_data(queryset=itemtxs_qs)
            po_itemtxs_formset_class = get_po_itemtxs_formset_class(po_model)
            itemtxs_formset = po_itemtxs_formset_class(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                po_model=po_model,
                queryset=itemtxs_qs,
            )
        else:
            itemtxs_qs, itemtxs_agg = po_model.get_itemtxs_data()

        context['po_total_amount__sum'] = itemtxs_agg['po_total_amount__sum']
        context['bill_amount_paid__sum'] = itemtxs_agg['bill_amount_paid__sum']
        context['itemtxs_qs'] = itemtxs_qs
        context['itemtxs_formset'] = itemtxs_formset

        if po_model.is_contract_bound():
            ce_model: EstimateModel = po_model.ce_model
            ce_itemtxs_qs, ce_itemtxs_agg = ce_model.get_itemtxs_annotation()
            context['ce_itemtxs_agg'] = ce_itemtxs_agg
            context['ce_cost_estimate__sum'] = sum(i['ce_cost_estimate__sum'] for i in ce_itemtxs_agg)

        return context

    def get(self, request, entity_slug, po_pk, *args, **kwargs):
        if self.action_update_items:
            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:po-update',
                                    kwargs={
                                        'entity_slug': entity_slug,
                                        'po_pk': po_pk
                                    })
            )
        return super(PurchaseOrderModelUpdateView, self).get(request, entity_slug, po_pk, *args, **kwargs)

    def post(self, request, entity_slug, *args, **kwargs):
        if self.action_update_items:

            if not request.user.is_authenticated:
                return HttpResponseForbidden()

            queryset = self.get_queryset()
            po_model: PurchaseOrderModel = self.get_object(queryset=queryset)
            self.object = po_model
            po_itemtxs_formset_class = get_po_itemtxs_formset_class(po_model)
            itemtxs_formset = po_itemtxs_formset_class(request.POST,
                                                       user_model=self.request.user,
                                                       po_model=po_model,
                                                       entity_slug=entity_slug)

            if itemtxs_formset.has_changed():
                if itemtxs_formset.is_valid():
                    itemtxs_list = itemtxs_formset.save(commit=False)
                    create_bill_uuids = [
                        str(i['uuid'].uuid) for i in itemtxs_formset.cleaned_data if i and i['create_bill'] is True
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

                    for itemtxs in itemtxs_list:
                        if not itemtxs.po_model_id:
                            itemtxs.po_model_id = po_model.uuid
                        itemtxs.clean()

                    itemtxs_list = itemtxs_formset.save()
                    po_model.update_state()
                    po_model.clean()
                    po_model.save(update_fields=['po_amount',
                                                 'po_amount_received',
                                                 'updated'])
                    # if valid get saved formset from DB
                    return self.render_to_response(context=self.get_context_data())
                # if not valid, return formset with errors...
                return self.render_to_response(context=self.get_context_data(itemtxs_formset=itemtxs_formset))
        return super(PurchaseOrderModelUpdateView, self).post(request, **kwargs)

    def get_form(self, form_class=None):
        po_model: PurchaseOrderModel = self.object
        if po_model.is_draft():
            return DraftPurchaseOrderModelUpdateForm(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                **self.get_form_kwargs()
            )
        elif po_model.is_review():
            return ReviewPurchaseOrderModelUpdateForm(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                **self.get_form_kwargs()
            )
        elif po_model.is_approved():
            return ApprovedPurchaseOrderModelUpdateForm(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                **self.get_form_kwargs()
            )
        return BasePurchaseOrderModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_form_kwargs(self):
        if self.action_update_items:
            return {
                'initial': self.get_initial(),
                'prefix': self.get_prefix(),
                'instance': self.object
            }
        return super(PurchaseOrderModelUpdateView, self).get_form_kwargs()

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        po_pk = self.kwargs['po_pk']
        return reverse('django_ledger:po-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'po_pk': po_pk
                       })

    def get_po_itemtxs_qs(self, po_model: PurchaseOrderModel):
        return po_model.itemtransactionmodel_set.select_related('bill_model', 'po_model').order_by('created')

    def form_valid(self, form: BasePurchaseOrderModelUpdateForm):
        po_model: PurchaseOrderModel = form.save(commit=False)

        if form.has_changed():
            po_items_qs = ItemTransactionModel.objects.for_po(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                po_pk=po_model.uuid,
            ).select_related('bill_model')

            if all(['po_status' in form.changed_data,
                    po_model.po_status == po_model.PO_STATUS_APPROVED]):
                po_items_qs.update(po_item_status=ItemTransactionModel.STATUS_NOT_ORDERED)

            if 'fulfilled' in form.changed_data:

                if not all([i.bill_model for i in po_items_qs]):
                    messages.add_message(self.request,
                                         messages.ERROR,
                                         f'All PO items must be billed before marking'
                                         f' PO: {po_model.po_number} as fulfilled.',
                                         extra_tags='is-danger')
                    return self.get(self.request)

                else:
                    if not all([i.bill_model.is_paid() for i in po_items_qs]):
                        messages.add_message(self.request,
                                             messages.SUCCESS,
                                             f'All bills must be paid before marking'
                                             f' PO: {po_model.po_number} as fulfilled.',
                                             extra_tags='is-success')
                        return self.get(self.request)

                po_items_qs.update(po_item_status=ItemTransactionModel.STATUS_RECEIVED)

        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'{self.object.po_number} successfully updated.',
                             extra_tags='is-success')

        return super().form_valid(form)


class PurchaseOrderModelDetailView(DjangoLedgerSecurityMixIn,
                                   PurchaseOrderModelModelViewQuerySetMixIn,
                                   DetailView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/purchase_order/po_detail.html'
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
        po_items_qs, item_data = po_model.get_itemtxs_data(
            queryset=po_model.itemtransactionmodel_set.all().select_related('item_model')
        )
        context['po_items'] = po_items_qs
        context['po_total_amount'] = sum(
            i['po_total_amount'] for i in po_items_qs.values(
                'po_total_amount', 'po_item_status') if i['po_item_status'] != 'cancelled')
        return context


class PurchaseOrderModelDeleteView(DjangoLedgerSecurityMixIn,
                                   PurchaseOrderModelModelViewQuerySetMixIn,
                                   DeleteView):
    slug_url_kwarg = 'po_pk'
    slug_field = 'uuid'
    context_object_name = 'po_model'
    template_name = 'django_ledger/purchase_order/po_delete.html'
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

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                       })

    def delete(self, request, *args, **kwargs):
        po_model: PurchaseOrderModel = self.get_object()
        self.object = po_model
        po_items_qs = po_model.itemtransactionmodel_set.filter(bill_model__isnull=False)
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


# ACTIONS...
class BasePurchaseOrderActionActionView(DjangoLedgerSecurityMixIn,
                                        PurchaseOrderModelModelViewQuerySetMixIn,
                                        RedirectView,
                                        SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'po_pk'
    action_name = None
    commit = True

    def get_redirect_url(self, entity_slug, po_pk, *args, **kwargs):
        return reverse('django_ledger:po-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'po_pk': po_pk
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BasePurchaseOrderActionActionView, self).get(request, *args, **kwargs)
        po_model: PurchaseOrderModel = self.get_object()

        try:
            getattr(po_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class PurchaseOrderMarkAsDraftView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_draft'


class PurchaseOrderMarkAsReviewView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_review'


class PurchaseOrderMarkAsApprovedView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_approved'


class PurchaseOrderMarkAsFulfilledView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_fulfilled'


class PurchaseOrderMarkAsCanceledView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_canceled'


class PurchaseOrderMarkAsVoidView(BasePurchaseOrderActionActionView):
    action_name = 'mark_as_void'
