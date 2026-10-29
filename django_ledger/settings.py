"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.
"""
import logging
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger('Django Ledger Logger')
logger.setLevel(logging.INFO)

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
DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX = getattr(settings, 'DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX', 'R')
DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX', True)

DJANGO_LEDGER_BILL_MODEL_ABSTRACT_CLASS = getattr(settings,
                                                  'DJANGO_LEDGER_BILL_MODEL_ABSTRACT_CLASS',
                                                  'django_ledger.models.bill.BillModelAbstract')

DJANGO_LEDGER_INVOICE_MODEL_ABSTRACT_CLASS = getattr(settings,
                                                     'DJANGO_LEDGER_INVOICE_MODEL_ABSTRACT_CLASS',
                                                     'django_ledger.models.invoice.InvoiceModelAbstract')

DJANGO_LEDGER_DEFAULT_COA = getattr(settings, 'DJANGO_LEDGER_DEFAULT_COA', None)
DJANGO_LEDGER_MATCH_DAYS_WINDOW = getattr(settings, 'DJANGO_LEDGER_MATCH_DAYS_WINDOW', 7)

DJANGO_LEDGER_FINANCIAL_ANALYSIS = {
    'ratios': {
        'current_ratio': {
            'good_incremental': True,
            'ranges': {
                'healthy': 2.0,
                'watch': 1.5,
                'warning': 1.0,
                'critical': 0.5,
            }
        },
        'quick_ratio': {
            'good_incremental': True,
            'ranges': {
                'healthy': 1.5,
                'watch': 1.0,
                'warning': 0.5,
                'critical': 0.25
            }
        },
        'debt_to_equity': {
            'good_incremental': False,
            'ranges': {
                'healthy': 0.5,
                'watch': 1.0,
                'warning': 1.5,
                'critical': 2.0
            }
        },
        'return_on_equity': {
            'good_incremental': True,
            'ranges': {
                'healthy': 0.15,
                'watch': 0.10,
                'warning': 0.05,
                'critical': 0.00
            }
        },
        'return_on_assets': {
            'good_incremental': True,
            'ranges': {
                'healthy': 0.05,
                'watch': 0.03,
                'warning': 0.02,
                'critical': 0.01
            }
        },
        'net_profit_margin': {
            'good_incremental': True,
            'ranges': {
                'healthy': 0.10,
                'watch': 0.05,
                'warning': 0.03,
                'critical': 0.01
            }
        },
        'gross_profit_margin': {
            'good_incremental': True,
            'ranges': {
                'healthy': 0.50,
                'watch': 0.30,
                'warning': 0.20,
                'critical': 0.10
            }
        },
    }
}

DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR = getattr(settings, 'DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR', True)
DJANGO_LEDGER_THEME = getattr(settings, 'DJANGO_LEDGER_THEME', 'litera')
DJANGO_LEDGER_DB_ROUTER_HINT_KEY = getattr(settings, 'DJANGO_LEDGER_DB_ROUTER_HINT_KEY', 'djl_db_router')
DJANGO_LEDGER_DB_ROUTING_ALIAS = getattr(settings, 'DJANGO_LEDGER_DB_ROUTING_ALIAS', None)