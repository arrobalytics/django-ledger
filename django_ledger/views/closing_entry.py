from django.views.generic import ArchiveIndexView

from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.views import DjangoLedgerSecurityMixIn


class ClosingEntryModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ClosingEntryModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).order_by('-updated')
        return super().get_queryset()


class ClosingEntryModelListView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, ArchiveIndexView):
    template_name = 'django_ledger/closing_entry/closing_entry_list.html'
    date_field = 'closing_date'
    allow_future = False
    # context_object_name = 'bills'
    # PAGE_TITLE = _('Bill List')
    # date_field = 'date_draft'
    # paginate_by = 20
    # paginate_orphans = 2
    # allow_empty = True
    # extra_context = {
    #     'page_title': PAGE_TITLE,
    #     'header_title': PAGE_TITLE,
    #     'header_subtitle_icon': 'uil:bill'
    # }
