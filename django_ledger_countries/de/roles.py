"""
German VAT-specific account roles.
"""
from django_ledger.regional.roles import register_extra_roles

ASSET_CA_VAT_RECEIVABLE = 'asset_ca_vat_recv'
LIABILITY_CL_VAT_PAYABLE = 'lia_cl_vat_payable'


def register_german_roles() -> None:
    register_extra_roles(
        asset_roles=[
            (ASSET_CA_VAT_RECEIVABLE, 'Input VAT (Vorsteuer)'),
        ],
        liability_roles=[
            (LIABILITY_CL_VAT_PAYABLE, 'Output VAT (Umsatzsteuer)'),
        ],
        group_memberships={
            'GROUP_CURRENT_ASSETS': [ASSET_CA_VAT_RECEIVABLE],
            'GROUP_CURRENT_LIABILITIES': [LIABILITY_CL_VAT_PAYABLE],
        },
    )
