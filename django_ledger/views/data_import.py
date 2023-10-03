"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import datetime, time
from itertools import chain, groupby

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, When, Case, F, Sum
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now, make_aware
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView, DetailView, RedirectView

from django_ledger.forms.data_import import OFXFileImportForm
from django_ledger.forms.data_import import StagedTransactionModelFormSet
from django_ledger.io import DEBIT, CREDIT
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models import LedgerModel, JournalEntryModel
from django_ledger.models.accounts import AccountModel
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


def digest_staged_txs(staged_txs_model: StagedTransactionModel, cash_account: AccountModel):
    tx_amt = staged_txs_model.amount
    reverse_tx = tx_amt < 0
    return [
        {
            'account': cash_account,
            'amount': abs(tx_amt),
            'tx_type': DEBIT if not reverse_tx else CREDIT,
            'description': staged_txs_model.name,
            'staged_tx_model': staged_txs_model
        },
        {
            'account': staged_txs_model.account_model,
            'amount': abs(tx_amt),
            'tx_type': CREDIT if not reverse_tx else DEBIT,
            'description': staged_txs_model.name,
            'staged_tx_model': staged_txs_model
        }
    ]


class DataImportJobsListView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import/data_import_job_list.html'


class DataImportOFXFileView(DjangoLedgerSecurityMixIn, FormView):
    template_name = 'django_ledger/data_import/data_import_ofx.html'
    PAGE_TITLE = _('OFX File Import')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    form_class = OFXFileImportForm

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

        import_job = ImportJobModel(bank_account_model=ba_model,
                                    description='OFX Import for Account ***' + ba_model.account_number[-4:])
        import_job.configure(commit=False)
        import_job.save()

        txs_to_stage = ofx.get_account_txs(account=ba_model.account_number)
        staged_txs_model_list = [
            StagedTransactionModel(
                date_posted=make_aware(value=datetime.combine(date=tx.dtposted.date(),
                                                              time=time.min)),
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


class DataImportJobDetailView(DjangoLedgerSecurityMixIn, ImportJobModelViewQuerySetMixIn, DetailView):
    template_name = 'django_ledger/data_import/data_import_job_txs.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'import_job'
    pk_url_kwarg = 'job_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_model: ImportJobModel = self.object
        context['header_title'] = job_model.bank_account_model
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
        context['staged_txs_qs'] = staged_txs_qs

        txs_formset = StagedTransactionModelFormSet(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            exclude_account=cash_account_model,
            queryset=staged_txs_qs.is_pending(),
        )

        context['staged_txs_formset'] = txs_formset
        context['cash_account_model'] = cash_account_model
        context['bank_account_model'] = bank_account_model
        return context

    def post(self, request, **kwargs):
        _ = super().get(request, **kwargs)
        job_model: ImportJobModel = self.object
        staged_txs_qs = job_model.stagedtransactionmodel_set.all()
        txs_formset = StagedTransactionModelFormSet(request.POST,
                                                    user_model=self.request.user,
                                                    queryset=staged_txs_qs,
                                                    entity_slug=kwargs['entity_slug'])

        if txs_formset.has_changed():
            if txs_formset.is_valid():
                for tx_form in txs_formset:
                    is_split = tx_form.cleaned_data['tx_split'] is True
                    if is_split:
                        tx_form.instance.add_split()

                staged_to_import = [
                    tx.instance for tx in txs_formset if all([
                        tx.cleaned_data['account_model'],
                        tx.cleaned_data['tx_import'],
                        tx.instance.transaction_model is None
                    ])
                ]

                if len(staged_to_import) > 0:

                    job_model.configure(commit=True)
                    ledger_model = job_model.ledger_model
                    cash_account = job_model.bank_account_model.cash_account

                    txs_digest = list(chain.from_iterable(
                        digest_staged_txs(
                            staged_txs_model=tx,
                            cash_account=cash_account) for tx in staged_to_import
                    ))

                    txs_digest.sort(key=lambda x: x['staged_tx_model'].date_posted)
                    txs_digest_gb = groupby(
                        txs_digest,
                        key=lambda x: (
                            x['staged_tx_model'].date_posted,
                            x['staged_tx_model'].unit_model if x['staged_tx_model'].unit_model_id is not None else ''
                        ))

                    for (dt_posted, unit_model), to_be_committed in txs_digest_gb:
                        je_model, txs_models = ledger_model.commit_txs(
                            je_timestamp=dt_posted,
                            je_unit_model=unit_model if unit_model else None,
                            je_txs=list(to_be_committed),
                            je_desc='OFX Import JE',
                            je_posted=False,
                            force_je_retrieval=False
                        )

                txs_formset.save()

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

