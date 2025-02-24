"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import datetime, time

from django.contrib import messages
from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView, DetailView, UpdateView, DeleteView

from django_ledger.forms.data_import import ImportJobModelCreateForm, ImportJobModelUpdateForm
from django_ledger.forms.data_import import StagedTransactionModelFormSet
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class ImportJobModelViewBaseView(DjangoLedgerSecurityMixIn):
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = ImportJobModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).order_by('-created').select_related('bank_account_model',
                                                  'bank_account_model__entity_model',
                                                  'bank_account_model__account_model',
                                                  'bank_account_model__account_model__coa_model')
        return super().get_queryset()


class ImportJobModelCreateView(ImportJobModelViewBaseView, FormView):
    template_name = 'django_ledger/data_import/import_job_create.html'
    PAGE_TITLE = _('Create Import Job')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    form_class = ImportJobModelCreateForm

    def get_form(self, form_class=None, **kwargs):
        return self.form_class(
            entity_model=self.get_authorized_entity_instance(),
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:data-import-jobs-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

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
                memo=tx.memo
            ) for tx in txs_to_stage
        ]
        for tx in staged_txs_model_list:
            tx.clean()

        StagedTransactionModel.objects.bulk_create(staged_txs_model_list)
        return super().form_valid(form=form)


class ImportJobModelListView(ImportJobModelViewBaseView, ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import/data_import_job_list.html'


class ImportJobModelUpdateView(ImportJobModelViewBaseView, UpdateView):
    template_name = 'django_ledger/data_import/import_job_update.html'
    context_object_name = 'import_job_model'
    pk_url_kwarg = 'job_pk'
    form_class = ImportJobModelUpdateForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Import Job Update'
        ctx['header_title'] = 'Import Job Update'
        ctx['header_subtitle'] = self.object.description
        ctx['header_subtitle_icon'] = 'solar:import-bold'
        return ctx

    def get_success_url(self):
        entity_model = self.get_authorized_entity_instance()
        return reverse(
            viewname='django_ledger:data-import-jobs-list',
            kwargs={
                'entity_slug': entity_model.slug
            }
        )

    def form_valid(self, form):
        messages.add_message(
            self.request,
            level=messages.SUCCESS,
            message=_(f'Successfully updated Import Job {self.object.description}'),
            extra_tags='is-success'
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
        return reverse(
            viewname='django_ledger:data-import-jobs-list',
            kwargs={
                'entity_slug': self.AUTHORIZED_ENTITY_MODEL.slug
            }
        )


class DataImportJobDetailView(ImportJobModelViewBaseView, DetailView):
    template_name = 'django_ledger/data_import/data_import_job_txs.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'import_job'
    pk_url_kwarg = 'job_pk'
    import_transactions = False
    form_class = StagedTransactionModelFormSet
    http_method_names = ['get', 'post']

    def get_form_kwargs(self):
        return {
            'entity_model': self.get_authorized_entity_instance(),
            'import_job_model': self.get_object(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # job_model: ImportJobModel = getattr(self, 'object', self.get_object())
        job_model: ImportJobModel = self.object

        context['page_title'] = job_model.description
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = job_model.description
        context['header_subtitle_icon'] = 'tabler:table-import'

        staged_txs_formset = StagedTransactionModelFormSet(
            entity_model=self.get_authorized_entity_instance(),
            import_job_model=job_model
        )

        context['staged_txs_formset'] = staged_txs_formset

        return context

    def post(self, request, **kwargs):
        self.object = self.get_object()

        txs_formset = StagedTransactionModelFormSet(
            entity_model=self.get_authorized_entity_instance(),
            import_job_model=self.object,
            data=request.POST
        )

        # if txs_formset.is_valid():
        for tx_form in txs_formset:
            if tx_form.has_changed():
                # perform work only if form has changed...
                if tx_form.is_valid():
                    tx_form.save()
                    # import entry was selected to be split....
                    is_split = tx_form.cleaned_data['tx_split'] is True
                    if is_split:
                        tx_form.instance.add_split()

                    # import entry was selected for import...
                    is_import = tx_form.cleaned_data['tx_import']
                    if is_import:
                        # all entries in split will be going so the same journal entry... (same unit...)
                        is_bundled = tx_form.cleaned_data['bundle_split']
                        tx_form.instance.migrate() if is_bundled else tx_form.instance.migrate(split_txs=True)

        messages.add_message(request,
                             messages.SUCCESS,
                             'Successfully saved transactions.',
                             extra_tags='is-success')

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
