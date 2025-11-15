"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import datetime, time
from typing import Optional

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView
from django_ledger.forms.data_import import (
    ImportJobModelCreateForm,
    ImportJobModelUpdateForm,
    StagedTransactionModelFormSet,
)
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models import (
    StagedTransactionModelValidationError,
)
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


# Import Job Views....
class ImportJobModelViewBaseView(DjangoLedgerSecurityMixIn):
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = (
                ImportJobModel.objects.for_entity(
                    entity_model=self.AUTHORIZED_ENTITY_MODEL,
                )
                .order_by('-created')
                .select_related(
                    'bank_account_model',
                    'bank_account_model__entity_model',
                    'bank_account_model__account_model',
                    'bank_account_model__account_model__coa_model',
                )
            )
        return self.queryset


class ImportJobModelCreateView(ImportJobModelViewBaseView, FormView):
    template_name = 'django_ledger/data_import/import_job_create.html'
    PAGE_TITLE = _('Create Import Job')
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}
    form_class = ImportJobModelCreateForm

    def get_form(self, form_class=None, **kwargs):
        return self.form_class(entity_model=self.get_authorized_entity_instance(), **self.get_form_kwargs())

    def get_success_url(self):
        return reverse(
            'django_ledger:import-job-list',
            kwargs={'entity_slug': self.AUTHORIZED_ENTITY_MODEL.slug},
        )

    def form_valid(self, form):
        ofx_manager = OFXFileManager(ofx_file_or_path=form.files['ofx_file'])
        import_job: ImportJobModel = form.save(commit=False)
        import_job.configure(commit=False)
        import_job.save()

        txs_to_stage = ofx_manager.get_account_txs()
        staged_txs_model_list = [
            StagedTransactionModel(
                date_posted=make_aware(value=datetime.combine(date=tx.dtposted.date(), time=time.min)),
                fit_id=tx.fitid,
                amount=tx.trnamt,
                import_job=import_job,
                name=tx.name,
                memo=tx.memo,
            )
            for tx in txs_to_stage
        ]
        for tx in staged_txs_model_list:
            tx.clean()

        StagedTransactionModel.objects.bulk_create(staged_txs_model_list)
        return super().form_valid(form=form)


class ImportJobModelListView(ImportJobModelViewBaseView, ListView):
    template_name = 'django_ledger/data_import/import_job_list.html'
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}
    context_object_name = 'import_job_list'


class ImportJobDetailView(ImportJobModelViewBaseView, DetailView):
    template_name = 'django_ledger/data_import/import_job_detail.html'
    PAGE_TITLE = _('Import Job Detail')
    context_object_name = 'import_job_model'
    pk_url_kwarg = 'job_pk'
    http_method_names = ['get']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import_job_model: ImportJobModel = self.object

        # Base queryset with all staged transactions for this job (annotated via manager)
        all_staged_qs = import_job_model.stagedtransactionmodel_set.select_related(
            'parent',
            'account_model',
            'unit_model',
            'vendor_model',
            'customer_model',
            'transaction_model',
            'matched_transaction_model',
            'import_job',
            'import_job__ledger_model',
        )

        pending_qs = all_staged_qs.is_pending()
        imported_qs = all_staged_qs.is_imported()
        ready_qs = all_staged_qs.is_ready_to_import()

        total_count = all_staged_qs.count()
        imported_count = imported_qs.count()
        pending_count = pending_qs.count()
        ready_count = ready_qs.count()

        progress_pct = 0
        if total_count:
            progress_pct = round((imported_count / total_count) * 100)

        context.update(
            {
                'page_title': self.PAGE_TITLE,
                'header_title': self.PAGE_TITLE,
                'header_subtitle': import_job_model.description,
                'header_subtitle_icon': 'solar:import-bold',
                'staged_all_qs': all_staged_qs,
                'staged_pending_qs': pending_qs,
                'staged_imported_qs': imported_qs,
                'staged_ready_qs': ready_qs,
                'progress': {
                    'total': total_count,
                    'imported': imported_count,
                    'pending': pending_count,
                    'ready': ready_count,
                    'pct': progress_pct,
                },
            }
        )
        return context


class ImportJobModelUpdateView(ImportJobModelViewBaseView, UpdateView):
    template_name = 'django_ledger/data_import/import_job_update.html'
    context_object_name = 'import_job_model'
    pk_url_kwarg = 'job_pk'
    form_class = ImportJobModelUpdateForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import_job_model: ImportJobModel = self.object
        ctx['page_title'] = 'Import Job Update'
        ctx['header_title'] = 'Import Job Update'
        ctx['header_subtitle'] = import_job_model.description
        ctx['header_subtitle_icon'] = 'solar:import-bold'
        return ctx

    def get_success_url(self):
        import_job_model: ImportJobModel = self.object
        return import_job_model.get_list_url()

    def form_valid(self, form):
        messages.add_message(
            self.request,
            level=messages.SUCCESS,
            message=_(f'Successfully updated Import Job {self.object.description}'),
            extra_tags='is-success',
        )
        return super().form_valid(form=form)


class ImportJobModelDeleteView(ImportJobModelViewBaseView, DeleteView):
    template_name = 'django_ledger/data_import/import_job_delete.html'
    context_object_name = 'import_job_model'
    pk_url_kwarg = 'job_pk'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Delete Import Job'
        ctx['header_title'] = 'Delete Import Job'
        ctx['header_subtitle'] = self.object.description
        ctx['header_subtitle_icon'] = 'solar:import-bold'
        return ctx

    def get_success_url(self):
        import_job_model: ImportJobModel = self.object
        return import_job_model.get_list_url()


class ImportJobModelResetView(ImportJobModelViewBaseView, DetailView):
    pk_url_kwarg = 'job_pk'
    http_method_names = ['post']

    def post(self, request, **kwargs):
        import_job_model: ImportJobModel = self.get_object()
        staged_txs_qs = import_job_model.stagedtransactionmodel_set.all()

        with transaction.atomic():
            # First pass: clear matches and undo imports
            for staged_tx in staged_txs_qs:
                # Clear matched links (no effect if none or not allowed)
                try:
                    staged_tx.unmatch(raise_exception=False)
                except Exception:
                    # Ignore any unexpected issues while unmatching during a bulk reset
                    pass

                # Undo created imports / receipts if any
                staged_tx.undo_import(raise_exception=False)

            # Second pass: delete children to collapse splits
            for staged_tx in list(staged_txs_qs):
                if staged_tx.is_children():
                    staged_tx.delete()

        messages.add_message(
            request,
            messages.SUCCESS,
            _('Import job reset. All matches cleared and imports undone.'),
            extra_tags='is-success',
        )

        return redirect(
            to=import_job_model.get_data_import_url(),
            permanent=False,
        )


# Staged Transactions Views....
# class StagedTransactionUpdateView(ImportJobModelViewBaseView, DetailView):
#     template_name = 'django_ledger/data_import/staged_tx_update.html'
#     context_object_name = 'staged_tx'
#     form_class = StagedTransactionModelFormSet
#     pk_url_kwarg = 'staged_tx_pk'
#     http_method_names = ['get', 'post']
#
#     def get_queryset(self):
#         import_job_model_qs = super().get_queryset()
#         import_job_model: ImportJobModel = get_object_or_404(import_job_model_qs, uuid__exact=self.kwargs['job_pk'])
#
#         self.import_job_model: ImportJobModel = import_job_model
#         return (
#             import_job_model.stagedtransactionmodel_set.all()
#             .is_pending()
#             .select_related('vendor_model', 'customer_model', 'unit_model')
#         )
#
#     def get_form_kwargs(self):
#         staged_tx_model: StagedTransactionModel = self.object
#         return {
#             'entity_model': self.get_authorized_entity_instance(),
#             'import_job_model': self.import_job_model,
#             'staged_tx_pk': staged_tx_model.uuid,
#         }
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['import_job_model'] = self.import_job_model
#         context['next'] = self.request.GET.get('next', '')
#         context['page_title'] = _('Update Staged Transaction')
#         context['header_title'] = _('Update Staged Transaction')
#         context['header_subtitle'] = self.import_job_model.description
#         context['header_subtitle_icon'] = 'tabler:transfer-in'
#
#         if self.request.POST:
#             staged_tx_form = StagedTransactionModelForm(
#                 data=self.request.POST,
#             )
#         else:
#             staged_tx_form = StagedTransactionModelForm()
#         return context
#
#     def form_invalid(self, form):
#         return super().form_invalid(form=form)
#
#     def form_valid(self, form):
#         # Persist mapping changes first
#         staged_tx: StagedTransactionModel = form.save()
#
#         # Clear proposed activity if mapping or split intent changed
#         if any(f in getattr(form, 'changed_data', []) for f in ['account_model', 'tx_split']):
#             staged_tx.activity = None
#             staged_tx.save(update_fields=['activity', 'updated'])
#
#         is_split = form.cleaned_data.get('tx_split') is True
#         is_import = form.cleaned_data.get('tx_import') is True
#         is_bundled = form.cleaned_data.get('bundle_split') is True
#
#         if is_split:
#             staged_tx.add_split()
#         elif is_import:
#             selected_match = form.cleaned_data.get('match_tx_model')
#             if selected_match is not None:
#                 staged_tx.matched_transaction_model = selected_match
#                 staged_tx.save(update_fields=['matched_transaction_model', 'updated'])
#             else:
#                 if staged_tx.can_migrate_receipt():
#                     staged_tx.migrate_receipt(
#                         receipt_date=staged_tx.date_posted,
#                         split_amount=not is_bundled,
#                     )
#                 else:
#                     staged_tx.migrate_transactions(split_txs=not is_bundled)
#
#         # Optional: collapse any parent now reduced to a single child (match bulk behavior)
#         parents_qs = (
#             self.import_job_model.stagedtransactionmodel_set.all()
#             .filter(parent__isnull=True)
#             .prefetch_related('split_transaction_set')
#         )
#
#         for parent in parents_qs:
#             children = list(parent.split_transaction_set.all())
#             if len(children) == 1:
#                 child = children[0]
#                 parent.account_model = child.account_model
#                 parent.unit_model = child.unit_model
#                 parent.receipt_type = child.receipt_type
#                 parent.vendor_model = child.vendor_model
#                 parent.customer_model = child.customer_model
#                 parent.bundle_split = True
#                 parent.save(
#                     update_fields=[
#                         'account_model',
#                         'unit_model',
#                         'receipt_type',
#                         'vendor_model',
#                         'customer_model',
#                         'bundle_split',
#                         'updated',
#                     ]
#                 )
#                 child.delete()
#
#         messages.add_message(self.request, messages.SUCCESS, _('Staged transaction updated.'), extra_tags='is-success')
#         return redirect(to=self.get_success_url())
#
#     def get_success_url(self):
#         staged_tx_model: StagedTransactionModel = self.object
#         if not staged_tx_model.is_pending():
#             return self.import_job_model.get_detail_url()
#         return staged_tx_model.get_update_url()


class StagedTransactionUpdateView(ImportJobModelViewBaseView, DetailView):
    template_name = 'django_ledger/data_import/staged_tx_update.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'staged_tx'
    pk_url_kwarg = 'staged_tx_pk'
    import_transactions = False
    form_class = StagedTransactionModelFormSet
    http_method_names = ['get', 'post']
    extra_context = {
        'show_details': False,
    }

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = (
                StagedTransactionModel.objects.for_entity(entity_model=self.AUTHORIZED_ENTITY_MODEL)
                .for_import_job(
                    import_job_model=self.kwargs['job_pk'],
                )
                .select_related(
                    'import_job',
                    'import_job__ledger_model',
                    'import_job__ledger_model__entity',
                )
                .is_pending()
                .is_parent()
            )
        return self.queryset


    def get_context_data(self, txs_formset: Optional[StagedTransactionModelFormSet] = None, **kwargs):
        context = super().get_context_data(**kwargs)

        staged_tx_model: StagedTransactionModel = self.object
        import_job_model: ImportJobModel = staged_tx_model.import_job

        context['page_title'] = import_job_model.description
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = import_job_model.description
        context['header_subtitle_icon'] = 'tabler:table-import'

        staged_txs_formset = (
            StagedTransactionModelFormSet(
                entity_model=self.get_authorized_entity_instance(),
                import_job_model=import_job_model,
                staged_tx_pk=staged_tx_model,
            )
            if not txs_formset
            else txs_formset
        )

        context['formset'] = staged_txs_formset
        context['import_job_model'] = import_job_model

        return context

    def post(self, request, **kwargs):
        self.object = self.get_object()
        staged_tx: StagedTransactionModel = self.object
        import_job_model: ImportJobModel = staged_tx.import_job

        txs_formset = StagedTransactionModelFormSet(
            entity_model=self.AUTHORIZED_ENTITY_MODEL,
            import_job_model=import_job_model,
            staged_tx_pk=self.kwargs['staged_tx_pk'],
            data=request.POST,
        )
        is_import = False

        if txs_formset.has_changed():
            for tx_form in txs_formset:
                if any(
                    [
                        'account_model' in tx_form.changed_data,
                        'tx_split' in tx_form.changed_data,
                    ]
                ):
                    staged_transaction_model: StagedTransactionModel = tx_form.instance
                    staged_transaction_model.activity = None

            if txs_formset.is_valid():
                txs_formset.save()
                for tx_form in txs_formset:
                    if tx_form.has_changed():
                        staged_transaction_model: StagedTransactionModel = tx_form.instance

                        is_split = tx_form.cleaned_data['tx_split'] is True
                        is_import = tx_form.cleaned_data['tx_import'] is True
                        is_bundled = tx_form.cleaned_data['bundle_split'] is True

                        if is_split:
                            staged_transaction_model.add_split()
                        elif is_import:
                            selected_match = tx_form.cleaned_data.get('match_tx_model')
                            if selected_match is not None:
                                # Link to existing posted transaction via matched_transaction_model without creating a new JE
                                staged_transaction_model.matched_transaction_model = selected_match
                                staged_transaction_model.save(update_fields=['matched_transaction_model', 'updated'])
                            else:
                                if staged_transaction_model.can_migrate_receipt():
                                    staged_transaction_model.migrate_receipt(
                                        receipt_date=staged_transaction_model.date_posted,
                                        split_amount=not is_bundled,
                                    )
                                else:
                                    staged_transaction_model.migrate_transactions(split_txs=not is_bundled)

                # After processing, auto-collapse any parent that now has exactly one child
                parents_qs = (
                    import_job_model.stagedtransactionmodel_set.all()
                    .filter(parent__isnull=True)
                    .prefetch_related('split_transaction_set')
                )

                for parent in parents_qs:
                    children = list(parent.split_transaction_set.all())
                    if len(children) == 1:
                        child = children[0]
                        # Copy mapping fields from the remaining child back to the parent
                        parent.account_model = child.account_model
                        parent.unit_model = child.unit_model
                        parent.receipt_type = child.receipt_type
                        parent.vendor_model = child.vendor_model
                        parent.customer_model = child.customer_model
                        parent.bundle_split = True  # single transactions are treated as bundled
                        parent.save(
                            update_fields=[
                                'account_model',
                                'unit_model',
                                'receipt_type',
                                'vendor_model',
                                'customer_model',
                                'bundle_split',
                                'updated',
                            ]
                        )
                        # Remove the lone child so the parent becomes single again
                        child.delete()
            else:
                # formset not valid.....
                context = self.get_context_data(txs_formset=txs_formset, **kwargs)
                return self.render_to_response(context)

        messages.add_message(
            request,
            messages.SUCCESS,
            'Successfully saved transactions.',
            extra_tags='is-success',
        )

        if staged_tx.is_imported():
            return HttpResponseRedirect(
                redirect_to=import_job_model.get_detail_url()
            )

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context=context)


# Actions....
class StagedTransactionUndoView(ImportJobModelViewBaseView, View):
    http_method_names = ['post']

    def post(self, request, entity_slug, job_pk, staged_tx_pk, *args, **kwargs):
        import_job_model: ImportJobModel = get_object_or_404(self.get_queryset(), uuid__exact=job_pk)
        staged_txs_qs = import_job_model.stagedtransactionmodel_set.all()
        staged_tx = get_object_or_404(staged_txs_qs, uuid__exact=staged_tx_pk)
        try:
            staged_tx.undo_import()
            messages.add_message(
                request,
                messages.SUCCESS,
                _('Successfully undone import for transaction %(name)s.')
                % {'name': staged_tx.name or staged_tx.fit_id},
                extra_tags='is-success',
            )
        except StagedTransactionModelValidationError as e:
            messages.add_message(
                request,
                messages.ERROR,
                e.message,
                extra_tags='is-danger',
            )
        return redirect(
            to=import_job_model.get_detail_url(),
        )


class StagedTransactionUnmatchView(ImportJobModelViewBaseView, View):
    http_method_names = ['post']

    def post(self, request, entity_slug, job_pk, staged_tx_pk, *args, **kwargs):
        import_job_model: ImportJobModel = get_object_or_404(self.get_queryset(), uuid__exact=job_pk)
        staged_txs_qs = import_job_model.stagedtransactionmodel_set.all()

        staged_tx = get_object_or_404(staged_txs_qs, uuid__exact=staged_tx_pk)
        try:
            staged_tx.unmatch(commit=True)
            messages.add_message(
                request,
                messages.SUCCESS,
                _('Successfully cleared match for transaction %(name)s.')
                % {'name': staged_tx.name or staged_tx.fit_id},
                extra_tags='is-success',
            )
        except StagedTransactionModelValidationError as e:
            messages.add_message(
                request,
                messages.ERROR,
                e.message,
                extra_tags='is-danger',
            )
        return redirect(
            reverse(
                'django_ledger:import-job-detail',
                kwargs={'entity_slug': import_job_model.entity_slug, 'job_pk': import_job_model.uuid},
            )
        )


# Retired Views....
