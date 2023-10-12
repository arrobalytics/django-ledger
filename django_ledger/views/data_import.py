"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import datetime, time

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView, DetailView, UpdateView, DeleteView

from django_ledger.forms.data_import import ImportJobModelCreateForm, ImportJobModelUpdateForm
from django_ledger.forms.data_import import StagedTransactionModelFormSet
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class ImportJobModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = ImportJobModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).order_by('-created').select_related('bank_account_model',
                                                  'bank_account_model__entity_model',
                                                  'bank_account_model__cash_account',
                                                  'bank_account_model__cash_account__coa_model')
        return super().get_queryset()


class ImportJobModelCreateView(DjangoLedgerSecurityMixIn, FormView):
    template_name = 'django_ledger/data_import/import_job_create.html'
    PAGE_TITLE = _('Create Import Job')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    form_class = ImportJobModelCreateForm

    def get_success_url(self):
        return reverse('django_ledger:data-import-jobs-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        ofx = OFXFileManager(ofx_file_or_path=form.files['ofx_file'])

        # Pulls accounts from OFX file...
        account_models = ofx.get_accounts()
        ofx_account_number = [a['account_number'] for a in account_models]

        # OFX file has multiple statements in it... Not supported...
        # All transactions must come from a single account...
        if len(ofx_account_number) > 1:
            messages.add_message(
                self.request,
                level=messages.ERROR,
                message=_('Multiple statements detected. Multiple account import is not supported.'),
                extra_tags='is-danger'
            )
            return self.form_invalid(form=form)

        ofx_account_number = ofx_account_number[0]

        # account has not been created yet...
        try:
            ba_model = self.AUTHORIZED_ENTITY_MODEL.bankaccountmodel_set.filter(
                account_number__exact=ofx_account_number
            ).select_related('cash_account', 'entity_model').get()
        except ObjectDoesNotExist:
            create_url = reverse(
                viewname='django_ledger:bank-account-create',
                kwargs={
                    'entity_slug': self.AUTHORIZED_ENTITY_MODEL.slug
                }
            )
            create_link = format_html('<a href={}>create</a>', create_url)
            messages.add_message(
                self.request,
                level=messages.ERROR,
                message=_(f'Account Number ***{ofx_account_number[-4:]} not recognized. Please {create_link} Bank '
                          'Account model before importing transactions'),
                extra_tags='is-danger'
            )
            return self.form_invalid(form=form)

        # account is not active...
        if not ba_model.is_active():
            create_url = reverse(
                viewname='django_ledger:bank-account-update',
                kwargs={
                    'entity_slug': self.AUTHORIZED_ENTITY_MODEL.slug,
                    'bank_account_pk': ba_model.uuid
                }
            )
            activate_link = format_html('<a href={}>mark account active</a>', create_url)
            messages.add_message(
                self.request,
                level=messages.ERROR,
                message=_(f'Account Number ***{ofx_account_number[-4:]} not active. Please {activate_link} '
                          ' before importing new transactions'),
                extra_tags='is-danger'
            )
            return self.form_invalid(form=form)

        import_job: ImportJobModel = form.save(commit=False)
        import_job.bank_account_model = ba_model
        import_job.configure(commit=False)
        import_job.save()

        txs_to_stage = ofx.get_account_txs(account=ba_model.account_number)
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


class ImportJobModelListView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import/data_import_job_list.html'


class ImportJobModelUpdateView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, UpdateView):
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
        return reverse(
            viewname='django_ledger:data-import-jobs-update',
            kwargs={
                'entity_slug': self.AUTHORIZED_ENTITY_MODEL.slug,
                'job_pk': self.kwargs['job_pk']
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


class ImportJobModelDeleteView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, DeleteView):
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


class DataImportJobDetailView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, DetailView):
    template_name = 'django_ledger/data_import/data_import_job_txs.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'import_job'
    pk_url_kwarg = 'job_pk'
    import_transactions = False

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job_model: ImportJobModel = self.object
        ctx['page_title'] = job_model.description
        ctx['header_title'] = self.PAGE_TITLE
        ctx['header_subtitle'] = job_model.description
        ctx['header_subtitle_icon'] = 'tabler:table-import'
        bank_account_model = job_model.bank_account_model
        cash_account_model = job_model.bank_account_model.cash_account
        if not cash_account_model:
            bank_acct_url = reverse('django_ledger:bank-account-update',
                                    kwargs={
                                        'entity_slug': self.kwargs['entity_slug'],
                                        'bank_account_pk': bank_account_model.uuid
                                    })
            messages.add_message(
                self.request,
                messages.ERROR,
                mark_safe(f'Warning! No cash account has been set for {job_model.bank_account_model}. '
                          f'Importing has been disabled until Cash Account is assigned. '
                          f'Click <a href="{bank_acct_url}">here</a> to assign'),
                extra_tags='is-danger'
            )

        staged_txs_qs = job_model.stagedtransactionmodel_set.all()
        ctx['staged_txs_qs'] = staged_txs_qs

        txs_formset = StagedTransactionModelFormSet(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            exclude_account=cash_account_model,
            queryset=staged_txs_qs.is_pending(),
        )

        ctx['staged_txs_formset'] = txs_formset
        ctx['cash_account_model'] = cash_account_model
        ctx['bank_account_model'] = bank_account_model
        return ctx

    def post(self, request, **kwargs):
        _ = super().get(request, **kwargs)
        job_model: ImportJobModel = self.object
        staged_txs_qs = job_model.stagedtransactionmodel_set.all()

        txs_formset = StagedTransactionModelFormSet(
            data=request.POST,
            user_model=self.request.user,
            queryset=staged_txs_qs,
            entity_slug=kwargs['entity_slug']
        )

        if txs_formset.has_changed():
            if txs_formset.is_valid():
                txs_formset.save()
                for tx_form in txs_formset:
                    is_split = tx_form.cleaned_data['tx_split'] is True
                    if is_split:
                        tx_form.instance.add_split()
                    is_import = tx_form.cleaned_data['tx_import']
                    if is_import:
                        is_split_bundled = tx_form.cleaned_data['bundle_split']
                        if not is_split_bundled:
                            tx_form.instance.migrate(split_txs=True)
                        else:
                            tx_form.instance.migrate()
            else:
                context = self.get_context_data(**kwargs)
                context['staged_txs_formset'] = txs_formset
                messages.add_message(request,
                                     messages.ERROR,
                                     'Hmmm, this doesn\'t add up!. Check your math!',
                                     extra_tags='is-danger')
                return self.render_to_response(context)

        messages.add_message(request,
                             messages.SUCCESS,
                             'Successfully saved transactions.',
                             extra_tags='is-success')
        return self.render_to_response(context=self.get_context_data())
