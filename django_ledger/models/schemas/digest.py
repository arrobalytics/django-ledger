"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

SCHEMA_ROLE_ACCOUNT = {
    'type': 'object'
}

SCHEMA_ROLE_BALANCE = {
    'type': 'object'
}

SCHEMA_ROLE_BALANCE_BY_PERIOD = {
    'type': ['object', 'null']
}

SCHEMA_GROUP_ACCOUNT = {
    'type': 'object'
}

SCHEMA_GROUP_BALANCE = {
    'type': 'object'
}

SCHEMA_GROUP_BALANCE_BY_PERIOD = {
    'type': ['object', 'null']
}

SCHEMA_RATIOS = {
    'type': 'object'
}

SCHEMA_ACCOUNTS = {
    'type': 'array'
}

SCHEMA_DIGEST = {
    'type': 'object',
    'properties': {
        'accounts': SCHEMA_ACCOUNTS,
        'role_account': SCHEMA_ROLE_ACCOUNT,
        'role_balance': SCHEMA_ROLE_BALANCE,
        'role_balance_by_period': SCHEMA_ROLE_BALANCE_BY_PERIOD,
        'group_account': SCHEMA_GROUP_ACCOUNT,
        'group_balance': SCHEMA_GROUP_BALANCE,
        'group_balance_by_period': SCHEMA_GROUP_BALANCE_BY_PERIOD,
        'ratios': SCHEMA_RATIOS,
    }

}
