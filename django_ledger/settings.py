from django.conf import settings

DJANGO_LEDGER_BILL_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_BILL_NUMBER_LENGTH', 10)
DJANGO_LEDGER_INVOICE_NUMBER_LENGTH = getattr(settings, 'DJANGO_LEDGER_INVOICE_NUMBER_LENGTH', 10)
DJANGO_LEDGER_FORM_INPUT_CLASSES = getattr(settings, 'DJANGO_LEDGER_FORM_INPUT_CLASSES', 'input')
DJANGO_LEDGER_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_CURRENCY_SYMBOL', '$')
DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL = getattr(settings, 'DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL', False)
DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON = getattr(settings, 'DJANGO_LEDGER_SHOW_FEEDBACK_BUTTON', False)
DJANGO_LEDGER_FEEDBACK_EMAIL_LIST = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_EMAIL_LIST', [])
DJANGO_LEDGER_FEEDBACK_FROM_EMAIL = getattr(settings, 'DJANGO_LEDGER_FEEDBACK_FROM_EMAIL', None)
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
