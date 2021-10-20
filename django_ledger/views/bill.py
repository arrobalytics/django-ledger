"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import (UpdateView, CreateView, DeleteView,
                                  View, ArchiveIndexView, MonthArchiveView, YearArchiveView,
                                  DetailView, RedirectView)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bill import BillModelCreateForm, BillModelUpdateForm, BillItemFormset, BillModelConfigureForm
from django_ledger.models import EntityModel, PurchaseOrderModel, LedgerModel
from django_ledger.models.bill import BillModel
from django_ledger.utils import new_bill_protocol, mark_accruable_paid
from django_ledger.views.mixins import LoginRequiredMixIn


class BillModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/bill_list.html'
    context_object_name = 'bills'
    PAGE_TITLE = _('Bill List')
    date_field = 'date'
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('vendor').order_by('-date')

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


class BillModelYearListView(YearArchiveView, BillModelListView):
    paginate_by = 10
    make_object_list = True


class BillModelMonthListView(MonthArchiveView, BillModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class BillModelCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/bill_create.html'
    PAGE_TITLE = _('Create Bill')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }
    for_purchase_order = False

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
            ).prefetch_related('itemthroughmodel_set')
            po_model: PurchaseOrderModel = get_object_or_404(po_qs, uuid__exact=po_pk)
            po_items = po_model.itemthroughmodel_set.filter(
                bill_model__isnull=True,
                uuid__in=po_item_uuids
            )
            context['po_model'] = po_model
            context['po_items'] = po_items
            form_action = reverse('django_ledger:bill-create-po',
                                  kwargs={
                                      'entity_slug': self.kwargs['entity_slug'],
                                      'po_pk': po_model.uuid
                                  }) + f'?item_uuids={po_item_uuids_qry_param}'
        else:
            form_action = reverse('django_ledger:bill-create',
                                  kwargs={
                                      'entity_slug': self.kwargs['entity_slug'],
                                  })
        context['form_action_url'] = form_action
        return context

    def get_initial(self):
        return {
            'date': localdate()
        }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = BillModelCreateForm(entity_slug=entity_slug,
                                   user_model=self.request.user,
                                   **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        bill_model = form.save(commit=False)
        ledger_model, bill_model = new_bill_protocol(
            bill_model=bill_model,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user)

        if self.for_purchase_order:
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

            if po_model.po_date > bill_model.date:
                messages.add_message(self.request,
                                     message=f'Bill Date {bill_model.date} cannot be'
                                             f' earlier than PO Date {po_model.po_date}',
                                     level=messages.ERROR,
                                     extra_tags='is-danger')
                return self.render_to_response(self.get_context_data(form=form))

            po_model_items_qs = po_model.itemthroughmodel_set.filter(uuid__in=item_uuids)

            bill_model.update_amount_due(queryset=po_model_items_qs)
            bill_model.new_state(commit=True)
            bill_model.clean()
            form.save()

            po_model_items_qs.update(bill_model=bill_model)

            bill_model.migrate_state(
                user_model=self.request.user,
                entity_slug=self.kwargs['entity_slug'],
                itemthrough_queryset=po_model_items_qs
            )
        else:
            form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        if self.for_purchase_order:
            po_pk = self.kwargs['po_pk']
            return reverse('django_ledger:po-update',
                           kwargs={
                               'entity_slug': entity_slug,
                               'po_pk': po_pk
                           })
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class BillModelUpdateView(LoginRequiredMixIn, UpdateView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_update.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill'
    }
    action_update_items = False
    http_method_names = ['get', 'post']

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
        return BillModelUpdateForm

    def get_context_data(self, *, object_list=None, item_formset: BillItemFormset = None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        bill_model = self.object
        title = f'Bill {bill_model.bill_number}'
        context['page_title'] = title
        context['header_title'] = title

        if not bill_model.is_configured():
            messages.add_message(
                request=self.request,
                message=f'Bill {bill_model.bill_number} must have all accounts configured.',
                level=messages.ERROR,
                extra_tags='is-danger'
            )

        ledger_model = self.object.ledger
        if ledger_model.locked:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! This bill is locked. Must unlock before making any changes.',
                                 extra_tags='is-danger')

        if not ledger_model.posted:
            messages.add_message(self.request,
                                 messages.INFO,
                                 f'This bill has not been posted. Must post to see ledger changes.',
                                 extra_tags='is-info')

        bill_model: BillModel = self.object
        if not item_formset:
            bill_item_queryset, item_data = bill_model.get_bill_item_data(
                queryset=bill_model.itemthroughmodel_set.select_related(
                    'item_model', 'po_model', 'bill_model').all()
            )

            item_formset = BillItemFormset(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                bill_pk=bill_model.uuid,
                queryset=bill_item_queryset
            )
        else:
            bill_item_queryset, item_data = bill_model.get_bill_item_data(
                queryset=item_formset.queryset
            )

        has_po = any(i['po_model'] for i in bill_item_queryset.values('po_model'))
        if has_po:
            item_formset.can_delete = False
            item_formset.has_po = has_po
        context['item_formset'] = item_formset
        context['total_amount_due'] = item_data['amount_due']
        context['has_po'] = has_po
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        bill_pk = self.kwargs['bill_pk']
        return reverse('django_ledger:bill-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_pk
                       })

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'itemthroughmodel_set'
        ).select_related('ledger', 'vendor')

    def form_valid(self, form):
        form.save(commit=False)
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Bill {self.object.bill_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)

    def post(self, request, bill_pk, entity_slug, *args, **kwargs):

        if self.action_update_items:
            self.object = self.get_object()
            item_formset: BillItemFormset = BillItemFormset(request.POST,
                                                            user_model=self.request.user,
                                                            bill_pk=bill_pk,
                                                            entity_slug=entity_slug)

            if item_formset.is_valid():
                if item_formset.has_changed():
                    invoice_items = item_formset.save(commit=False)
                    bill_qs = BillModel.objects.for_entity(
                        user_model=self.request.user,
                        entity_slug=entity_slug
                    )
                    bill_model: BillModel = get_object_or_404(bill_qs, uuid__exact=bill_pk)

                    entity_qs = EntityModel.objects.for_user(
                        user_model=self.request.user
                    )
                    entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                    for item in invoice_items:
                        item.entity = entity_model
                        item.bill_model = bill_model

                    bill_item_list = item_formset.save()
                    # todo: pass item list to update_amount_due...?
                    bill_model.update_amount_due()
                    bill_model.new_state(commit=True)
                    bill_model.clean()
                    bill_model.save(update_fields=['amount_due',
                                                   'amount_receivable',
                                                   'amount_unearned',
                                                   'amount_earned',
                                                   'updated'])

                    bill_model.migrate_state(
                        entity_slug=entity_slug,
                        user_model=self.request.user,
                        # itemthrough_models=bill_item_list,
                        force_migrate=True
                    )

                    messages.add_message(request,
                                         message=f'Items for Invoice {bill_model.bill_number} saved.',
                                         level=messages.SUCCESS,
                                         extra_tags='is-success')

                    return HttpResponseRedirect(reverse('django_ledger:bill-update',
                                                        kwargs={
                                                            'entity_slug': entity_slug,
                                                            'bill_pk': bill_pk
                                                        }))

            else:
                context = self.get_context_data(item_formset=item_formset)
                return self.render_to_response(context=context)

        return super(BillModelUpdateView, self).post(request, *args, **kwargs)


class BillModelDetailView(LoginRequiredMixIn, DetailView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_detail.html'
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
        bill_items_qs, item_data = bill_model.get_bill_item_data(
            queryset=bill_model.itemthroughmodel_set.all()
        )
        context['bill_items'] = bill_items_qs
        context['total_amount_due'] = item_data['amount_due']

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
        ).prefetch_related(
            'itemthroughmodel_set', 'ledger__journal_entries__entity_unit'
        ).select_related('ledger', 'vendor', 'cash_account', 'prepaid_account', 'unearned_account')


class BillModelDeleteView(LoginRequiredMixIn, DeleteView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    extra_context = {
        'hide_menu': True,
        'header_subtitle_icon': 'uil:bill'
    }
    void = False

    def get_template_names(self):
        if self.void:
            return 'django_ledger/bill_void.html'
        return 'django_ledger/bill_delete.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Bill ') + self.object.bill_number
        context['header_title'] = context['page_title']
        context['form_action_url'] = self.get_form_action_url()
        return context

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_form_action_url(self):
        bill_model: BillModel = self.object
        KWARGS = {
            'entity_slug': self.kwargs['entity_slug'],
            'bill_pk': bill_model.uuid
        }
        if self.void:
            return reverse(
                viewname='django_ledger:bill-void',
                kwargs=KWARGS
            )
        return reverse(
            viewname='django_ledger:bill-delete',
            kwargs=KWARGS
        )

    def get_success_url(self):
        if self.void:
            return reverse('django_ledger:bill-detail',
                           kwargs={
                               'entity_slug': self.kwargs['entity_slug'],
                               'bill_pk': self.kwargs['bill_pk']
                           })
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                       })

    def delete(self, request, *args, **kwargs):
        bill_model: BillModel = self.get_object()
        success_url = self.get_success_url()

        self.object = bill_model

        bill_items_qs = bill_model.itemthroughmodel_set.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )

        # forcing QS evaluation
        len(bill_items_qs)
        if self.void:

            if bill_model.void:
                messages.add_message(
                    self.request,
                    message=f'Bill {bill_model.bill_number} already voided...',
                    level=messages.ERROR,
                    extra_tags='is-danger')
                url_redirect = reverse('django_ledger:bill-detail',
                                       kwargs={
                                           'entity_slug': self.kwargs['entity_slug'],
                                           'bill_pk': bill_model.uuid
                                       })
                return HttpResponseRedirect(redirect_to=url_redirect)

            bill_model.void = True
            ld = localdate()
            bill_model.void_date = ld
            bill_model.save(update_fields=[
                'void',
                'void_date',
                'updated'
            ])

            bill_model.migrate_state(
                user_model=self.request.user,
                commit=True,
                void=True,
                itemthrough_queryset=bill_items_qs,
                je_date=ld,
                entity_slug=self.kwargs['entity_slug']
            )
            return HttpResponseRedirect(success_url)

        has_POs = bill_items_qs.filter(po_model__isnull=False).count() > 0
        if has_POs:
            messages.add_message(self.request,
                                 level=messages.ERROR,
                                 message='Cannot delete bill that has a PO. Void bill instead.',
                                 extra_tags='is-danger')
            return self.render_to_response(context=self.get_context_data())

        bill_model.itemthroughmodel_set.update(bill_model=None)
        self.object.delete()
        return HttpResponseRedirect(success_url)


class BillModelMarkPaidView(LoginRequiredMixIn,
                            View,
                            SingleObjectMixin):
    http_method_names = ['post']
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')

    def post(self, request, *args, **kwargs):
        bill: BillModel = self.get_object()
        mark_accruable_paid(
            accruable_model=bill,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        messages.add_message(request,
                             messages.SUCCESS,
                             f'Successfully marked bill {bill.bill_number} as Paid.',
                             extra_tags='is-success')
        redirect_url = reverse('django_ledger:bill-detail',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug'],
                                   'bill_pk': bill.uuid
                               })
        return HttpResponseRedirect(redirect_url)


class BillModelActionView(LoginRequiredMixIn, SingleObjectMixin, RedirectView):
    context_object_name = 'bill_model'
    slug_field = 'uuid'
    slug_url_kwarg = 'bill_pk'
    http_method_names = ['post']

    action = None
    ACTION_FORCE_MIGRATE = 'force-migrate'
    ACTION_LOCK = 'lock'
    ACTION_UNLOCK = 'unlock'

    def get_redirect_url(self, *args, **kwargs):
        bill_model: BillModel = self.get_object()
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'bill_pk': bill_model.uuid
                       })

    def post(self, request, *args, **kwargs):
        bill_model: BillModel = self.get_object()
        ledger_model: LedgerModel = bill_model.ledger

        if self.action == self.ACTION_FORCE_MIGRATE:

            if bill_model.ledger.locked:
                messages.add_message(self.request,
                                     level=messages.ERROR,
                                     message=f'Cannot migrate {bill_model.bill_number}. Bill ledger is locked.',
                                     extra_tags='is-danger')
            else:
                items, _ = bill_model.migrate_state(
                    user_model=self.request.user,
                    entity_slug=self.kwargs['entity_slug'],
                    force_migrate=True
                )
                if not items:
                    bill_model.amount_due = 0
                    bill_model.save(update_fields=['amount_due', 'updated'])

        elif self.action == self.ACTION_LOCK:
            if not ledger_model.locked:
                ledger_model.locked = True
                ledger_model.save(update_fields=['locked', 'updated'])
                messages.add_message(self.request,
                                     level=messages.SUCCESS,
                                     message=f'{bill_model.bill_number} is locked.',
                                     extra_tags='is-success')
            else:
                messages.add_message(self.request,
                                     level=messages.WARNING,
                                     message=f'{bill_model.bill_number} already locked.',
                                     extra_tags='is-warning')

        elif self.action == self.ACTION_UNLOCK:
            if ledger_model.locked:
                ledger_model.locked = False
                ledger_model.save(update_fields=['locked', 'updated'])
                messages.add_message(self.request,
                                     level=messages.SUCCESS,
                                     message=f'{bill_model.bill_number} is unlocked.',
                                     extra_tags='is-success')
            else:
                messages.add_message(self.request,
                                     level=messages.WARNING,
                                     message=f'{bill_model.bill_number} already unlocked.',
                                     extra_tags='is-warning')

        return super(BillModelActionView, self).post(self.request)

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')
