from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView

from django_ledger.forms.data_import import OFXFileImportForm
from django_ledger.io.ofx import OFXFileManager
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.data_import_jobs import ImportJobModel


class DataImportJobsView(ListView):
    PAGE_TITLE = _('Data Import Jobs')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    context_object_name = 'import_jobs'
    template_name = 'django_ledger/data_import_job_list.html'

    def get_queryset(self):
        return ImportJobModel.objects.all()


class OFXFileImportView(FormView):
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
        accs = ofx.get_accounts_info()
        for acc in accs:
            bank_acc_model, created = BankAccountModel.objects.exists(
                account_number__exact=acc['account_number'],
                ledger__entity__slug__exact=self.kwargs['entity_slug']
            )
        return super().form_valid(form=form)
