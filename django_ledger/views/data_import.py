from itertools import chain

from django.contrib import messages
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView, DetailView

from django_ledger.forms.data_import import OFXFileImportForm
from django_ledger.forms.data_import import StagedTransactionModelFormSet
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models.accounts import AccountModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import new_bankaccount_protocol


def digest_staged_txs(cleaned_staged_tx: dict, cash_account: AccountModel):
    tx_amt = cleaned_staged_tx['amount']
    reverse_tx = tx_amt < 0
    return [
        {
            'account_id': cash_account.uuid,
            'amount': abs(tx_amt),
            'tx_type': 'debit' if not reverse_tx else 'credit',
            'description': cleaned_staged_tx['name'],
            'staged_tx_model': cleaned_staged_tx['uuid']
        },
        {
            'account_id': cleaned_staged_tx['earnings_account'].uuid,
            'amount': abs(tx_amt),
            'tx_type': 'credit' if not reverse_tx else 'debit',
            'description': cleaned_staged_tx['name'],
            'staged_tx_model': cleaned_staged_tx['uuid']
        }
    ]


class DataImportJobsListView(ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import_job_list.html'

    def get_queryset(self):
        return ImportJobModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class DataImportOFXFileView(FormView):
    template_name = 'django_ledger/data_import_ofx.html'
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
        accs = ofx.get_accounts()
        acc_numbers = [
            a['account_number'] for a in accs
        ]

        # Gets bank account models if in DB...
        bank_accounts = BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        ).filter(account_number__in=acc_numbers).select_related('ledger')

        ba_values = bank_accounts.values()
        existing_accounts_list = [
            a['account_number'] for a in ba_values
        ]

        # determines if Bank Account models need to be created...
        to_create = [
            a for a in accs if a['account_number'] not in existing_accounts_list
        ]

        if len(to_create) > 0:

            entity_model = EntityModel.objects.for_user(
                user_model=self.request.user
            ).get(slug__exact=self.kwargs['entity_slug'])

            new_bank_accs = [
                BankAccountModel(
                    name=f'{ba["bank"]} - *{ba["account_number"][-4:]}',
                    account_type=ba['account_type'].lower(),
                    account_number=ba['account_number'],
                    routing_number=ba['routing_number'],
                ) for ba in to_create]

            for ba in new_bank_accs:
                ba.clean()

            new_bank_accs = [
                new_bankaccount_protocol(
                    bank_account_model=ba,
                    entity_slug=entity_model,
                    user_model=self.request.user
                ) for ba in new_bank_accs
            ]
            BankAccountModel.objects.bulk_create(new_bank_accs)

            # fetching all bank account models again
            bank_accounts = BankAccountModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
            ).filter(account_number__in=acc_numbers).select_related('ledger')

        for ba in bank_accounts:
            import_job = ba.ledger.importjobmodel_set.create(
                description='OFX Import for Account *' + ba.account_number[-4:]
            )
            txs = ofx.get_account_txs(account=ba.account_number)
            txs_models = [
                StagedTransactionModel(
                    date_posted=tx.dtposted,
                    fitid=tx.fitid,
                    amount=tx.trnamt,
                    import_job=import_job,
                    name=tx.name,
                    memo=tx.memo
                ) for tx in txs
            ]
            for tx in txs_models:
                tx.clean()
            txs_models = StagedTransactionModel.objects.bulk_create(txs_models)

        return super().form_valid(form=form)


class DataImportJobDetailView(DetailView):
    template_name = 'django_ledger/data_import_job_txs.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'import_job'
    pk_url_kwarg = 'job_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        return ImportJobModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        ).select_related('ledger__bankaccountmodel__cash_account')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_model: ImportJobModel = self.object
        context['header_title'] = job_model.ledger.bankaccountmodel

        job_model = self.object
        bank_account_model = job_model.ledger.bankaccountmodel
        cash_account_model = job_model.ledger.bankaccountmodel.cash_account
        if not cash_account_model:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! No cash account has been set for {job_model.ledger.bankaccountmodel}.'
                                 f'Importing has been disabled until Cash Account is assigned.',
                                 extra_tags='is-danger')

        stx_qs = job_model.stagedtransactionmodel_set.all()
        stx_qs = stx_qs.select_related('tx__account').order_by('-date_posted', '-amount')

        # forcing queryset evaluation
        len(stx_qs)

        txs_formset = StagedTransactionModelFormSet(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            exclude_accounts=[cash_account_model],
            queryset=stx_qs.filter(tx__isnull=True),
        )

        context['staged_txs_formset'] = txs_formset
        context['imported_txs'] = stx_qs.filter(tx__isnull=False)
        context['cash_account_model'] = cash_account_model
        context['bank_account_model'] = bank_account_model
        return context

    def post(self, request, **kwargs):
        job_model = self.get_object()
        self.object = job_model
        txs_formset = StagedTransactionModelFormSet(request.POST,
                                                    user_model=self.request.user,
                                                    entity_slug=kwargs['entity_slug'])
        if txs_formset.is_valid():
            txs_formset.save()
            staged_to_import = [
                tx for tx in txs_formset.cleaned_data if all([
                    tx['earnings_account'],
                    tx['tx_import'],
                    not tx['tx']
                ])
            ]

            if len(staged_to_import) > 0:
                job_model = ImportJobModel.objects.for_entity(
                    entity_slug=self.kwargs['entity_slug'],
                    user_model=self.request.user
                ).select_related(
                    'ledger__bankaccountmodel__cash_account'
                ).get(uuid__exact=self.kwargs['job_pk'])

                ledger_model = job_model.ledger
                cash_account = job_model.ledger.bankaccountmodel.cash_account

                txs_digest = list(chain.from_iterable(
                    digest_staged_txs(cleaned_staged_tx=tx,
                                      cash_account=cash_account) for tx in staged_to_import
                ))

                je_model, txs_models = ledger_model.create_je_acc_id(
                    je_posted=True,
                    je_date=now().date(),
                    je_txs=txs_digest,
                    je_desc='OFX Import JE',
                    je_activity='op'
                )

                staged_tx_models = [stx['uuid'] for stx in staged_to_import]
                StagedTransactionModel.objects.bulk_update(staged_tx_models, fields=['tx'])

            # txs_formset.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Successfully saved transactions.',
                                 extra_tags='is-success')
            return self.get(request, **kwargs)
        else:
            context = self.get_context_data(**kwargs)
            context['staged_txs_formset'] = txs_formset
            messages.add_message(request,
                                 messages.ERROR,
                                 'Hmmm, this doesn\'t add up!. Check your math!',
                                 extra_tags='is-danger')
            return self.render_to_response(context)
