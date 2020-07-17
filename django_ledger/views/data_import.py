from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView, TemplateView
from django.contrib import messages

from django_ledger.forms.data_import import OFXFileImportForm
from django_ledger.forms.data_import import StagedTransactionModelFormSet
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import new_bankaccount_protocol


class DataImportJobsListView(ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import_job_list.html'

    def get_queryset(self):
        return ImportJobModel.objects.all()


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
        accs = ofx.get_accounts()

        bank_accounts = BankAccountModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        ).filter(account_number__in=[
            a['account_number'] for a in accs
        ]).select_related('ledger')

        ba_values = bank_accounts.values()
        existing_accounts_list = [
            a['account_number'] for a in ba_values
        ]

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
            ).filter(account_number__in=[
                a['account_number'] for a in accs
            ]).select_related('ledger')

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


class DataImportJobStagedTxsListView(TemplateView):
    template_name = 'django_ledger/data_import_job_txs.html'
    PAGE_TITLE = _('Import Job Staged Txs')
    context_object_name = 'txs'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        txs_formset = StagedTransactionModelFormSet(
            user_model=self.request.user,
            entity_slug=kwargs['entity_slug'],
            queryset=self.get_queryset(),
        )

        context['staged_txs_formset'] = txs_formset

        # messages.add_message(
        #     self.request,
        #     messages.ERROR,
        #     'This is so cool!',
        #     extra_tags='is-danger'
        # )

        return self.render_to_response(context)

    def get_queryset(self):
        return StagedTransactionModel.objects.for_job(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            job_pk=self.kwargs['job_pk']
        ).order_by('-date_posted')

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = StagedTransactionModelFormSet(request.POST,
                                                    user_model=self.request.user,
                                                    entity_slug=kwargs['entity_slug'],
                                                    queryset=self.get_queryset())

        if txs_formset.is_valid():
            txs_formset.save()
            context['staged_txs_formset'] = txs_formset
            messages.add_message(request, messages.SUCCESS,
                                 'Successfully saved transactions.',
                                 extra_tags='is-success')
        else:
            context['staged_txs_formset'] = txs_formset
            messages.add_message(request,
                                 messages.ERROR,
                                 'Hmmm, this doesn\'t add up!. Check your math!',
                                 extra_tags='is-danger')
        return self.render_to_response(context)
