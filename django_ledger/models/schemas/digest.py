"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

SCHEMA_DIGEST = {
    'type': 'object',
    'properties': {
        'accounts': {
            'type': 'array'
        },
        'role_account': {
            'type': 'object'
        },
        'role_balance': {
            'type': 'object',
        },
        'role_balance_by_period': {
            'type': ['object', 'null']
        },
        'group_account': {
            'type': 'object'
        },
        'group_balance': {
            'type': 'object'
        },
        'group_balance_by_period': {
            'type': ['object', 'null']
        },
        'ratios': {
            'type': 'object'
        },
    }

}
