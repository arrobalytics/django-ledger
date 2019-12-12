from django.conf import settings

USER_SETTINGS = getattr(settings, 'DJANGO_LEDGER_SETTINGS', dict())

DJANGO_LEDGER_SETTINGS = {
    'ACCOUNT_MAX_LENGTH': USER_SETTINGS.get('ACCOUNT_MAX_LENGTH', 10),
    'ACCOUNT_MODEL_ABSTRACT': 'django_ledger.model_base.accounts.AccountModelAbstract',
    'COA_MODEL_ABSTRACT': 'django_ledger.model_base.coa.ChartOfAccountModelAbstract',
    'ENTITY_MODEL_ABSTRACT': 'django_ledger.model_base.entity.EntityModelAbstract',
    'ENTITY_MANAGEMENT_MODEL_ABSTRACT': 'django_ledger.model_base.entity.EntityManagementModelAbstract',
    'LEDGER_MODEL_ABSTRACT': 'django_ledger.model_base.ledger.LedgerModelAbstract',
    'JOURNAL_ENTRY_MODEL_ABSTRACT': 'django_ledger.model_base.journal_entry.JournalEntryModelAbstract',
    'TRANSACTION_MODEL_ABSTRACT': 'django_ledger.model_base.transactions.TransactionModelAbstract',
}