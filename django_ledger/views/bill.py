"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import (UpdateView, CreateView, ArchiveIndexView, MonthArchiveView, YearArchiveView,
                                  DetailView, RedirectView)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bill import (BillModelCreateForm, BaseBillModelUpdateForm, DraftBillModelUpdateForm,
                                      get_bill_itemtxs_formset_class, BillModelConfigureForm,
                                      InReviewBillModelUpdateForm,
                                      ApprovedBillModelUpdateForm, AccruedAndApprovedBillModelUpdateForm,
                                      PaidBillModelUpdateForm)
from django_ledger.models import EntityModel, PurchaseOrderModel, EstimateModel
from django_ledger.models.bill import BillModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class BillModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = BillModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('vendor', 'ledger', 'ledger__entity').order_by('-updated')
        return super().get_queryset()


class BillModelCreateView(DjangoLedgerSecurityMixIn, CreateView):
    template_name = 'django_ledger/bills/bill_create.html'
    PAGE_TITLE = _('Create Bill')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }
    for_purchase_order = False
    for_estimate = False

    def get(self, request, entity_slug, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        if self.for_estimate and 'ce_pk' in self.kwargs:
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=entity_slug,
                user_model=self.request.user
            )
            estimate_model: EstimateModel = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            if not estimate_model.can_bind():
                return HttpResponseNotFound('404 Not Found')
        return super(BillModelCreateView, self).get(request, entity_slug, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BillModelCreateView, self).get_context_data(**kwargs)

        if self.for_purchase_order:
            po_pk = self.kwargs['po_pk']
            po_item_uuids_qry_param = self.request.GET.get('item_uuids')
            if po_item_uuids_qry_param:
                try:
                    po_item_uuids = po_item_uuids_qry_param.split(',')
                except:
                    return HttpResponseBadRequest()
            else:
                return HttpResponseBadRequest()

            po_qs = PurchaseOrderModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).prefetch_related('itemtransactionmodel_set')
            po_model: PurchaseOrderModel = get_object_or_404(po_qs, uuid__exact=po_pk)
            po_itemtxs_qs = po_model.itemtransactionmodel_set.filter(
                bill_model__isnull=True,
                uuid__in=po_item_uuids
            )
            context['po_model'] = po_model
            context['po_itemtxs_qs'] = po_itemtxs_qs
            form_action = reverse('django_ledger:bill-create-po',
                                  kwargs={
                                      'entity_slug': self.kwargs['entity_slug'],
                                      'po_pk': po_model.uuid
                                  }) + f'?item_uuids={po_item_uuids_qry_param}'
        elif self.for_estimate:
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            )
            estimate_uuid = self.kwargs['ce_pk']
            estimate_model: EstimateModel = get_object_or_404(estimate_qs, uuid__exact=estimate_uuid)
            form_action = reverse('django_ledger:bill-create-estimate',
                                  kwargs={
                                      'entity_slug': self.kwargs['entity_slug'],
                                      'ce_pk': estimate_model.uuid
                                  })
        else:
            form_action = reverse('django_ledger:bill-create',
                                  kwargs={
                                      'entity_slug': self.kwargs['entity_slug'],
                                  })
        context['form_action_url'] = form_action
        return context

    def get_initial(self):
        return {
            'date_draft': localdate()
        }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        return BillModelCreateForm(entity_slug=entity_slug,
                                   user_model=self.request.user,
                                   **self.get_form_kwargs())

    def form_valid(self, form):
        bill_model: BillModel = form.save(commit=False)
        ledger_model, bill_model = bill_model.configure(
            entity_slug=self.kwargs['entity_slug'],
            commit_ledger=True,
            ledger_posted=False,
            user_model=self.request.user)

        if self.for_estimate:
            ce_pk = self.kwargs['ce_pk']
            estimate_model_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user)

            estimate_model = get_object_or_404(estimate_model_qs, uuid__exact=ce_pk)
            bill_model.bind_estimate(estimate_model=estimate_model, commit=False)

        elif self.for_purchase_order:
            po_pk = self.kwargs['po_pk']
            item_uuids = self.request.GET.get('item_uuids')
            if not item_uuids:
                return HttpResponseBadRequest()
            item_uuids = item_uuids.split(',')
            po_qs = PurchaseOrderModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            )
            po_model: PurchaseOrderModel = get_object_or_404(po_qs, uuid__exact=po_pk)

            try:
                bill_model.can_bind_po(po_model, raise_exception=True)
            except ValidationError as e:
                messages.add_message(self.request,
                                     message=e.message,
                                     level=messages.ERROR,
                                     extra_tags='is-danger')
                return self.render_to_response(self.get_context_data(form=form))

            po_model_items_qs = po_model.itemtransactionmodel_set.filter(uuid__in=item_uuids)

            if po_model.is_contract_bound():
                bill_model.ce_model_id = po_model.ce_model_id

            bill_model.update_amount_due()
            bill_model.get_state(commit=True)
            bill_model.clean()
            bill_model.save()
            po_model_items_qs.update(bill_model=bill_model)
            return HttpResponseRedirect(self.get_success_url())

        return super(BillModelCreateView, self).form_valid(form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        if self.for_purchase_order:
            po_pk = self.kwargs['po_pk']
            return reverse('django_ledger:po-update',
                           kwargs={
                               'entity_slug': entity_slug,
                               'po_pk': po_pk
                           })
        elif self.for_estimate:
            return reverse('django_ledger:customer-estimate-detail',
                           kwargs={
                               'entity_slug': entity_slug,
                               'ce_pk': self.kwargs['ce_pk']
                           })
        bill_model: BillModel = self.object
        return reverse('django_ledger:bill-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_model.uuid
                       })


class BillModelListView(DjangoLedgerSecurityMixIn, BillModelModelViewQuerySetMixIn, ArchiveIndexView):
    template_name = 'django_ledger/bills/bill_list.html'
    context_object_name = 'bills'
    PAGE_TITLE = _('Bill List')
    date_field = 'date_draft'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }


class BillModelYearListView(YearArchiveView, BillModelListView):
    paginate_by = 10
    make_object_list = True


class BillModelMonthListView(MonthArchiveView, BillModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class BillModelDetailView(DjangoLedgerSecurityMixIn, DetailView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bills/bill_detail.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill',
        'hide_menu': True
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        bill_model: BillModel = self.object
        title = f'Bill {bill_model.bill_number}'
        context['page_title'] = title
        context['header_title'] = title

        bill_model: BillModel = self.object
        bill_items_qs, item_data = bill_model.get_itemtxs_data()
        context['itemtxs_qs'] = bill_items_qs
        context['total_amount__sum'] = item_data['total_amount__sum']

        if not bill_model.is_configured():
            link = format_html(f"""
            <a href="{reverse("django_ledger:bill-update", kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'bill_pk': bill_model.uuid
            })}">here</a>
            """)
            msg = f'Bill {bill_model.bill_number} has not been fully set up. ' + \
                  f'Please update or assign associated accounts {link}.'
            messages.add_message(self.request,
                                 message=msg,
                                 level=messages.WARNING,
                                 extra_tags='is-danger')
        return context

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related(
            'ledger',
            'ledger__entity',
            'vendor',
            'cash_account',
            'prepaid_account',
            'unearned_account'
        )


class BillModelUpdateView(DjangoLedgerSecurityMixIn, UpdateView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill_model'
    template_name = 'django_ledger/bills/bill_update.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill'
    }
    http_method_names = ['get', 'post']
    action_update_items = False

    def get_itemtxs_qs(self):
        bill_model: BillModel = self.object
        return bill_model.itemtransactionmodel_set.select_related(
            'item_model', 'po_model', 'bill_model').order_by(
            '-total_amount')

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        if self.request.method == 'POST' and self.action_update_items:
            return form_class(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                instance=self.object
            )
        return form_class(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_form_class(self):
        bill_model: BillModel = self.object
        if not bill_model.is_configured():
            return BillModelConfigureForm
        if bill_model.is_draft():
            return DraftBillModelUpdateForm
        elif bill_model.is_review():
            return InReviewBillModelUpdateForm
        elif bill_model.is_approved() and not bill_model.accrue:
            return ApprovedBillModelUpdateForm
        elif bill_model.is_approved() and bill_model.accrue:
            return AccruedAndApprovedBillModelUpdateForm
        elif bill_model.is_paid():
            return PaidBillModelUpdateForm
        return BaseBillModelUpdateForm

    def get_context_data(self, *, object_list=None,
                         itemtxs_formset=None,
                         **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        bill_model: BillModel = self.object
        ledger_model = bill_model.ledger

        title = f'Bill {bill_model.bill_number}'
        context['page_title'] = title
        context['header_title'] = title
        context['header_subtitle'] = bill_model.get_bill_status_display()

        if not bill_model.is_configured():
            messages.add_message(
                request=self.request,
                message=f'Bill {bill_model.bill_number} must have all accounts configured.',
                level=messages.ERROR,
                extra_tags='is-danger'
            )

        if not bill_model.is_paid():
            if ledger_model.locked:
                messages.add_message(self.request,
                                     messages.ERROR,
                                     f'Warning! This bill is locked. Must unlock before making any changes.',
                                     extra_tags='is-danger')

        if ledger_model.locked:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! This bill is locked. Must unlock before making any changes.',
                                 extra_tags='is-danger')

        if not ledger_model.is_posted():
            messages.add_message(self.request,
                                 messages.INFO,
                                 f'This bill has not been posted. Must post to see ledger changes.',
                                 extra_tags='is-info')

        if not itemtxs_formset:
            itemtxs_qs = self.get_itemtxs_qs()
            itemtxs_qs, itemtxs_agg = bill_model.get_itemtxs_data(queryset=itemtxs_qs)
            invoice_itemtxs_formset_class = get_bill_itemtxs_formset_class(bill_model)
            itemtxs_formset = invoice_itemtxs_formset_class(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                bill_model=bill_model,
                queryset=itemtxs_qs
            )
        else:
            itemtxs_qs, itemtxs_agg = bill_model.get_itemtxs_data(queryset=itemtxs_formset.queryset)

        has_po = any(i.po_model_id for i in itemtxs_qs)
        if has_po:
            itemtxs_formset.can_delete = False
            itemtxs_formset.has_po = has_po

        context['itemtxs_formset'] = itemtxs_formset
        context['total_amount__sum'] = itemtxs_agg['total_amount__sum']
        context['has_po'] = has_po
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        bill_pk = self.kwargs['bill_pk']
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_pk
                       })

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related(
            'ledger', 'ledger__entity', 'vendor', 'cash_account',
            'prepaid_account', 'unearned_account')

    def form_valid(self, form):
        form.save(commit=False)
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Bill {self.object.bill_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)

    def get(self, request, entity_slug, bill_pk, *args, **kwargs):
        if self.action_update_items:
            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:bill-update',
                                    kwargs={
                                        'entity_slug': entity_slug,
                                        'bill_pk': bill_pk
                                    })
            )
        return super(BillModelUpdateView, self).get(request, entity_slug, bill_pk, *args, **kwargs)

    def post(self, request, bill_pk, entity_slug, *args, **kwargs):
        if self.action_update_items:

            if not request.user.is_authenticated:
                return HttpResponseForbidden()

            queryset = self.get_queryset()
            bill_model: BillModel = self.get_object(queryset=queryset)
            self.object = bill_model
            bill_itemtxs_formset_class = get_bill_itemtxs_formset_class(bill_model)
            itemtxs_formset = bill_itemtxs_formset_class(request.POST,
                                                         user_model=self.request.user,
                                                         bill_model=bill_model,
                                                         entity_slug=entity_slug)

            if itemtxs_formset.has_changed():
                if itemtxs_formset.is_valid():
                    itemtxs_list = itemtxs_formset.save(commit=False)
                    entity_qs = EntityModel.objects.for_user(user_model=self.request.user)
                    entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                    for itemtxs in itemtxs_list:
                        itemtxs.bill_model_id = bill_model.uuid
                        itemtxs.clean()

                    itemtxs_formset.save()
                    itemtxs_qs = bill_model.update_amount_due()
                    bill_model.get_state(commit=True)
                    bill_model.clean()
                    bill_model.save(update_fields=['amount_due',
                                                   'amount_receivable',
                                                   'amount_unearned',
                                                   'amount_earned',
                                                   'updated'])

                    bill_model.migrate_state(
                        entity_slug=entity_slug,
                        user_model=self.request.user,
                        itemtxs_qs=itemtxs_qs,
                        raise_exception=False
                    )

                    messages.add_message(request,
                                         message=f'Items for Invoice {bill_model.bill_number} saved.',
                                         level=messages.SUCCESS,
                                         extra_tags='is-success')

                    # if valid get saved formset from DB
                    return HttpResponseRedirect(
                        redirect_to=reverse('django_ledger:bill-update',
                                            kwargs={
                                                'entity_slug': entity_slug,
                                                'bill_pk': bill_pk
                                            })
                    )
            context = self.get_context_data(itemtxs_formset=itemtxs_formset)
            return self.render_to_response(context=context)
        return super(BillModelUpdateView, self).post(request, **kwargs)


# ACTION VIEWS...
class BaseBillActionView(DjangoLedgerSecurityMixIn, RedirectView, SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'bill_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger', 'ledger__entity')

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': kwargs['entity_slug'],
                           'bill_pk': kwargs['bill_pk']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseBillActionView, self).get(request, *args, **kwargs)
        bill_model: BillModel = self.get_object()

        try:
            getattr(bill_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class BillModelActionMarkAsDraftView(BaseBillActionView):
    action_name = 'mark_as_draft'


class BillModelActionMarkAsInReviewView(BaseBillActionView):
    action_name = 'mark_as_review'


class BillModelActionMarkAsApprovedView(BaseBillActionView):
    action_name = 'mark_as_approved'


class BillModelActionMarkAsPaidView(BaseBillActionView):
    action_name = 'mark_as_paid'


class BillModelActionDeleteView(BaseBillActionView):
    action_name = 'mark_as_delete'


class BillModelActionVoidView(BaseBillActionView):
    action_name = 'mark_as_void'


class BillModelActionLockLedgerView(BaseBillActionView):
    action_name = 'lock_ledger'


class BillModelActionUnlockLedgerView(BaseBillActionView):
    action_name = 'unlock_ledger'


class BillModelActionForceMigrateView(BaseBillActionView):
    action_name = 'migrate_state'

    def get_redirect_url(self, entity_slug, bill_pk, *args, **kwargs):
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_pk
                       })
