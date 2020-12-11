"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

SCHEMA_PNL_DATA = {
    'type': 'object',
}

SCHEMA_PNL = {
    'type': 'object',
    'properties': {
        'entity_slug': {
            'type': 'string'
        },
        'entity_name': {
            'type': 'string'
        },
        'pnl_data': SCHEMA_PNL_DATA
    },
    'required': [
        'entity_slug',
        'entity_name',
        'pnl_data'
    ]
}
