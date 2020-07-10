from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
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
