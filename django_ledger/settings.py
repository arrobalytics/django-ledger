"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal

from django.conf import settings

DJANGO_LEDGER_BILL_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_BILL_NUMBER_LENGTH', 10)
DJANGO_LEDGER_INVOICE_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_INVOICE_NUMBER_LENGTH', 10)
DJANGO_LEDGER_FORM_INPUT_CLASSES = getattr(settings, 'DJANGO_LEDGER_FORM_INPUT_CLASSES', 'input')
DJANGO_LEDGER_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_CURRENCY_SYMBOL', '$')
DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL', False)
DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON = getattr(settings, 'DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON', False)
DJANGO_LEDGER_FEEDBACK_EMAIL_LIST = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_EMAIL_LIST', [])
DJANGO_LEDGER_FEEDBACK_FROM_EMAIL = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_FROM_EMAIL', None)
DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME = getattr(settings, 'DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME', False)
DJANGO_LEDGER_LOGIN_URL = getattr(settings, 'DJANGO_LEDGER_LOGIN_URL', settings.LOGIN_URL)

DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE = getattr(settings,
                                                  'DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE',
                                                  Decimal('0.02'))

DJANGO_LEDGER_TRANSACTION_CORRECTION = getattr(settings,
                                               'DJANGO_LEDGER_TRANSACTION_CORRECTION',
                                               Decimal('0.01'))

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
DJANGO_LEDGER_JE_NUMBER_PREFIX = 'JE'
DJANGO_LEDGER_PO_NUMBER_PREFIX = 'PO'
DJANGO_LEDGER_ESTIMATE_NUMBER_PREFIX = 'E'
DJANGO_LEDGER_INVOICE_NUMBER_PREFIX = 'I'
DJANGO_LEDGER_BILL_NUMBER_PREFIX = 'B'
DJANGO_LEDGER_VENDOR_NUMBER_PREFIX = 'V'
DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX = 'C'
DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX = 'IEX'
DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX = 'INV'
DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX = 'IPR'
DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING = 10
DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX = '000'
