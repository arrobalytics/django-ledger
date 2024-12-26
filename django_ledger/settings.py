"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.
"""
import logging
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger('Django Ledger Logger')
logger.setLevel(logging.INFO)

try:
    from graphene import __version__
    from graphene_django import __version__
    from oauth2_provider import __version__

    DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED = True
except ImportError:
    DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED = False

try:
    from fpdf import FPDF

    DJANGO_LEDGER_PDF_SUPPORT_ENABLED = True
except ImportError:
    DJANGO_LEDGER_PDF_SUPPORT_ENABLED = False

logger.info(f'Django Ledger GraphQL Enabled: {DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED}')


## MODEL ABSTRACTS ##
DJANGO_LEDGER_ACCOUNT_MODEL = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_MODEL', 'django_ledger.AccountModel')
DJANGO_LEDGER_CHART_OF_ACCOUNTS_MODEL = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_MODEL', 'django_ledger.ChartOfAccountModelAbstract')
DJANGO_LEDGER_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_TRANSACTION_MODEL', 'django_ledger.TransactionModelAbstract')
DJANGO_LEDGER_JOURNAL_ENTRY_MODEL = getattr(settings, 'DJANGO_LEDGER_JOURNAL_ENTRY_MODEL', 'django_ledger.JournalEntryModelAbstract')
DJANGO_LEDGER_LEDGER_MODEL = getattr(settings, 'DJANGO_LEDGER_LEDGER_MODEL', 'django_ledger.LedgerModel')
DJANGO_LEDGER_ENTITY_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_MODEL', 'django_ledger.EntityModelAbstract')
DJANGO_LEDGER_ENTITY_STATE_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_STATE_MODEL', 'django_ledger.EntityStateModel')

DJANGO_LEDGER_ENTITY_UNIT_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_UNIT_MODEL', 'django_ledger.EntityUnitModelAbstract')

DJANGO_LEDGER_ESTIMATE_MODEL = getattr(settings, 'DJANGO_LEDGER_ESTIMATE_MODEL', 'django_ledger.EstimateModelAbstract')
DJANGO_LEDGER_BILL_MODEL = getattr(settings, 'DJANGO_LEDGER_BILL_MODEL', 'django_ledger.BillModelAbstract')
DJANGO_LEDGER_INVOICE_MODEL = getattr(settings, 'DJANGO_LEDGER_INVOICE_MODEL', 'django_ledger.InvoiceModelAbstract')
DJANGO_LEDGER_PURCHASE_ORDER_MODEL = getattr(settings, 'DJANGO_LEDGER_PURCHASE_ORDER_MODEL', 'django_ledger.PurchaseOrderModelAbstract')

DJANGO_LEDGER_CUSTOMER_MODEL = getattr(settings, 'DJANGO_LEDGER_CUSTOMER_MODEL', 'django_ledger.CustomerModelAbstract')
DJANGO_LEDGER_VENDOR_MODEL = getattr(settings, 'DJANGO_LEDGER_VENDOR_MODEL', 'django_ledger.VendorModelAbstract')

DJANGO_LEDGER_BANK_ACCOUNT_MODEL = getattr(settings, 'DJANGO_LEDGER_BANK_ACCOUNT_MODEL', 'django_ledger.BackAccountModelAbstract')
DJANGO_LEDGER_CLOSING_ENTRY_MODEL = getattr(settings, 'DJANGO_LEDGER_CLOSING_ENTRY_MODEL', 'django_ledger.ClosingEntryTransactionModelAbstract')
DJANGO_LEDGER_UNIT_OF_MEASURE_MODEL = getattr(settings, 'DJANGO_LEDGER_UNIT_OF_MEASURE_MODEL', 'django_ledger.UnitOfMeasureModelAbstract')
DJANGO_LEDGER_ITEM_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_ITEM_TRANSACTION_MODEL', 'django_ledger.ItemTransactionModelAbstract')
DJANGO_LEDGER_ITEM_MODEL = getattr(settings, 'DJANGO_LEDGER_ITEM_MODEL', 'django_ledger.ItemModelAbstract')
DJANGO_LEDGER_STAGED_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_STAGED_TRANSACTION_MODEL', 'django_ledger.StagedTransactionModelAbstract')
DJANGO_LEDGER_IMPORT_JOB_MODEL = getattr(settings, 'DJANGO_LEDGER_IMPORT_JOB_MODEL', 'django_ledger.ImportJobModelAbstract')

DJANGO_LEDGER_USE_CLOSING_ENTRIES = getattr(settings, 'DJANGO_LEDGER_USE_CLOSING_ENTRIES', True)
DJANGO_LEDGER_DEFAULT_CLOSING_ENTRY_CACHE_TIMEOUT = getattr(settings,
                                                            'DJANGO_LEDGER_DEFAULT_CLOSING_ENTRY_CACHE_TIMEOUT', 3600)
DJANGO_LEDGER_AUTHORIZED_SUPERUSER = getattr(settings, 'DJANGO_LEDGER_AUTHORIZED_SUPERUSER', False)
DJANGO_LEDGER_LOGIN_URL = getattr(settings, 'DJANGO_LEDGER_LOGIN_URL', settings.LOGIN_URL)
DJANGO_LEDGER_BILL_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_BILL_NUMBER_LENGTH', 10)
DJANGO_LEDGER_INVOICE_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_INVOICE_NUMBER_LENGTH', 10)
DJANGO_LEDGER_FORM_INPUT_CLASSES = getattr(settings, 'DJANGO_LEDGER_FORM_INPUT_CLASSES', 'input')
DJANGO_LEDGER_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_CURRENCY_SYMBOL', '$')
DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL', False)
DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON = getattr(settings, 'DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON', False)
DJANGO_LEDGER_FEEDBACK_EMAIL_LIST = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_EMAIL_LIST', [])
DJANGO_LEDGER_FEEDBACK_FROM_EMAIL = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_FROM_EMAIL', None)
DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME = getattr(settings, 'DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME', False)
DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE = getattr(settings, 'DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE', Decimal('0.02'))
DJANGO_LEDGER_TRANSACTION_CORRECTION = getattr(settings, 'DJANGO_LEDGER_TRANSACTION_CORRECTION', Decimal('0.01'))
DJANGO_LEDGER_ACCOUNT_CODE_GENERATE = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_CODE_GENERATE', True)
DJANGO_LEDGER_ACCOUNT_CODE_GENERATE_LENGTH = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_CODE_GENERATE_LENGTH', 5)
DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_CODE_GENERATE_LENGTH', True)
DJANGO_LEDGER_JE_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_JE_NUMBER_PREFIX', 'JE')
DJANGO_LEDGER_PO_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_PO_NUMBER_PREFIX', 'PO')
DJANGO_LEDGER_ESTIMATE_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_ESTIMATE_NUMBER_PREFIX', 'E')
DJANGO_LEDGER_INVOICE_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_INVOICE_NUMBER_PREFIX', 'I')
DJANGO_LEDGER_BILL_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_BILL_NUMBER_PREFIX', 'B')
DJANGO_LEDGER_VENDOR_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_VENDOR_NUMBER_PREFIX', 'V')
DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX', 'C')
DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX', 'IEX')
DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX', 'INV')
DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX', 'IPR')
DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING = getattr(settings, 'DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING', 10)
DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX = getattr(settings, 'DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX', '000')

DJANGO_LEDGER_BILL_MODEL_ABSTRACT_CLASS = getattr(settings,
                                                  'DJANGO_LEDGER_BILL_MODEL_ABSTRACT_CLASS',
                                                  'django_ledger.models.bill.BillModelAbstract')

DJANGO_LEDGER_INVOICE_MODEL_ABSTRACT_CLASS = getattr(settings,
                                                     'DJANGO_LEDGER_INVOICE_MODEL_ABSTRACT_CLASS',
                                                     'django_ledger.models.invoice.InvoiceModelAbstract')

DJANGO_LEDGER_DEFAULT_COA = getattr(settings, 'DJANGO_LEDGER_DEFAULT_COA', None)

DJANGO_LEDGER_FINANCIAL_ANALYSIS = {
    'ratios': {
        'current_ratio': {
            'good_incremental': True,
            'ranges': {
                'healthy': 2,
                'watch': 1,
                'warning': .5,
                'critical': .25
            }
        },
        'quick_ratio': {
            'good_incremental': True,
            'ranges': {
                'healthy': 2,
                'watch': 1,
                'warning': .5,
                'critical': .25
            }
        },
        'debt_to_equity': {
            'good_incremental': False,
            'ranges': {
                'healthy': 0,
                'watch': .25,
                'warning': .5,
                'critical': 1
            }
        },
        'return_on_equity': {
            'good_incremental': True,
            'ranges': {
                'healthy': .10,
                'watch': .07,
                'warning': .04,
                'critical': .02
            }
        },
        'return_on_assets': {
            'good_incremental': True,
            'ranges': {
                'healthy': .10,
                'watch': .06,
                'warning': .04,
                'critical': .02
            }
        },
        'net_profit_margin': {
            'good_incremental': True,
            'ranges': {
                'healthy': .10,
                'watch': .06,
                'warning': .04,
                'critical': .02
            }
        },
        'gross_profit_margin': {
            'good_incremental': True,
            'ranges': {
                'healthy': .10,
                'watch': .06,
                'warning': .04,
                'critical': .02
            }
        },
    }
}
