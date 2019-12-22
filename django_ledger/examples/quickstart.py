from django.contrib.auth import get_user_model

from django_ledger.models.coa import make_account_active
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import populate_default_coa

UserModel = get_user_model()


def quickstart(quickstart_user: str, reset_entity=False):
    user_model = UserModel.objects.get(username=quickstart_user)
    quickstart_entity = 'my-quickstart-inc'

    if reset_entity:
        EntityModel.objects.filter(slug=quickstart_entity, admin=user_model).delete()
        company = populate_default_coa(coa_data=CHART_OF_ACCOUNTS,
                                       admin=user_model,
                                       entity='my-quickstart-inc')
    else:
        company = EntityModel.objects.get(slug=quickstart_entity)
    make_account_active(company.coa, ['1010', '3010', '1610', '1611', '2110', '6253', '6290', '6070', '4020'])
    myco_ledger, created = company.ledgers.get_or_create(name='My Debug Ledger')
    myco_ledger.journal_entry.all().delete()
    txs_data = [
        {
            'code': '1010',
            'amount': 200000,
            'tx_type': 'debit',
            'description': 'Company Funding'
        },
        {
            'code': '3010',
            'amount': 200000,
            'tx_type': 'credit',
            'description': 'Capital contribution'
        },
        {
            'code': '1010',
            'amount': 40000,
            'tx_type': 'credit',
            'description': 'Downpayment'
        },
        {
            'code': '2110',
            'amount': 80000,
            'tx_type': 'credit',
            'description': 'Issue debt'
        },
        {
            'code': '1610',
            'amount': 120000,
            'tx_type': 'debit',
            'description': 'Property cost base'
        },
        {
            'code': '4020',
            'amount': 1500,
            'tx_type': 'credit',
            'description': 'Rental Income'
        },
        {
            'code': '1010',
            'amount': 1500,
            'tx_type': 'debit',
            'description': 'Rental Income'
        },
        {
            'code': '1010',
            'amount': 180.45,
            'tx_type': 'credit',
            'description': 'HOA expense'
        },
        {
            'code': '6253',
            'amount': 180.45,
            'tx_type': 'debit',
            'description': 'HOA Exoense'
        },
        {
            'code': '1611',
            'amount': 465.50,
            'tx_type': 'credit',
            'description': 'Accumulated Depreciation'
        },
        {
            'code': '6070',
            'amount': 465.50,
            'tx_type': 'debit',
            'description': 'HOA Expense'
        },

    ]

    company.create_je(je_date='2019-04-09',
                      je_txs=txs_data,
                      je_origin='quickstart',
                      je_ledger=myco_ledger,
                      je_desc='Purchase of property at 123 Main St',
                      je_activity='inv')

    # Balance Sheet as_of='2019-01-31' ----
    bs = myco_ledger.balance_sheet(as_dataframe=True,
                                   signs=True,
                                   as_of='2019-05-09')

    # Balance Sheet Latest / Operational Activities Only
    bs_op = myco_ledger.balance_sheet(as_dataframe=True, activity='op')

    # Balance Sheet Latest / As list
    bs_f = myco_ledger.balance_sheet(signs=True)

    # Income Statement / Sign adjustment (negative -> expenses / positive -> income)
    ic = myco_ledger.income_statement(as_dataframe=True, signs=True)
    return bs, bs_op, bs_f, ic


# bs, bs_op, bs_f, ic = quickstart(quickstart_user='elarroba', reset_entity=True)
