from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel, make_account_active
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import create_coa_structure


def quickstart(reset_db=False):
    """
    Django Ledger QuickStart Function
    :param reset_db: USE WITH CAUTION!!!!
    :return:
    """
    if reset_db:
        # Uncoment these if needed ....

        # EntityModel.objects.all().delete()
        # ChartOfAccountModel.objects.all().delete()
        # AccountModel.objects.all().delete()

        coa = create_coa_structure(coa_data=CHART_OF_ACCOUNTS, coa_name='CoA QuickStart')

    make_account_active(coa, ['1010', '3010', '1610', '2110', '6253', '6290', '4020'])
    coa, created = ChartOfAccountModel.objects.get_or_create(name='CoA QuickStart')
    company, created = EntityModel.objects.get_or_create(slug='my-co-inc',
                                                         coa=coa,
                                                         name='MyCo Inc')
    ledger_id = 'my-co-ledger'  # auto generated if not provided
    myco_ledger, created = company.general_ledger.get_or_create(slug=ledger_id, name='My Debug Ledger')
    myco_ledger.journal_entry.all().delete()

    # Company Funding
    funding = 200000
    myco_ledger.tx_generic(
        amount=funding,
        start_date='2019-10-02',
        debit_acc='1010',
        credit_acc='3010',
        activity='other',
        desc='Company funding.'
    )

    # Buy property
    myco_ledger.tx_generic(
        amount=40000,
        start_date='2019-10-02',
        debit_acc='1610',
        credit_acc='1010',
        activity='inv',
        desc='Real estate down payment'
    )

    # Issuing Debt ---
    myco_ledger.tx_generic(
        amount=80000,
        start_date='2019-10-02',
        debit_acc='1610',
        credit_acc='2110',
        activity='fin',
        desc='Mortgage to buy real estate.'
    )

    # An expense ----
    myco_ledger.tx_generic(
        amount=100,
        start_date='2019-11-02',
        debit_acc='6253',
        credit_acc='1010',
        activity='op',
        desc='HOA Expenses Nov 2019'
    )

    # An Income ----
    myco_ledger.tx_generic(
        amount=1200,
        start_date='2019-11-06',
        debit_acc='1010',
        credit_acc='4020',
        activity='op',
        desc='HOA Expenses Nov 2019'
    )

    # Another Expense ----
    myco_ledger.tx_generic(
        amount=115.50,
        start_date='2019-12-22',
        debit_acc='6290',
        credit_acc='1010',
        activity='op',
        desc='November Electricity Bill'
    )

    # Debt Payment ----
    myco_ledger.tx_generic(
        amount=10550,
        start_date='2020-1-03',
        debit_acc='2110',
        credit_acc='1010',
        activity='op',
        desc='Debt Payment'
    )

    # Balance Sheet as_of='2019-01-31' ----
    bs = myco_ledger.balance_sheet(as_dataframe=True, as_of='2019-01-31')

    # Balance Sheet Latest / Operational Activities Only
    bs_op = myco_ledger.balance_sheet(as_dataframe=True, activity='op')

    # Balance Sheet Latest / As list
    bs_f = myco_ledger.balance_sheet(as_dataframe=False)

    # Income Statement / Sign adjustment (negative -> expenses / positive -> income)
    ic = myco_ledger.income_statement(as_dataframe=True, signs=True)
    return bs, bs_op, bs_f, ic


def quickstart_2(reset_db=False):
    if reset_db:
        EntityModel.objects.all().delete()
        ChartOfAccountModel.objects.all().delete()
        AccountModel.objects.all().delete()
        coa = create_coa_structure(coa_data=CHART_OF_ACCOUNTS, coa_name='CoA QuickStart')

    coa, created = ChartOfAccountModel.objects.get_or_create(name='CoA QuickStart')
    make_account_active(coa, ['1010', '3010', '1610', '2110', '6253', '6290', '4020'])
    company, created = EntityModel.objects.get_or_create(slug='my-co-inc',
                                                         coa=coa,
                                                         name='MyCo Inc')
    ledger_id = 'my-co-ledger'  # auto generated if not provided
    myco_ledger, created = company.general_ledger.get_or_create(slug=ledger_id, name='My Debug Ledger')
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
        }
    ]

    myco_ledger.tx_optimized(je_date='2019-04-09',
                             je_txs=txs_data,
                             je_activity='inv')

    # Balance Sheet as_of='2019-01-31' ----
    bs = myco_ledger.balance_sheet(as_dataframe=True, as_of='2019-05-31')

    # Balance Sheet Latest / Operational Activities Only
    bs_op = myco_ledger.balance_sheet(as_dataframe=True, activity='op')

    # Balance Sheet Latest / As list
    bs_f = myco_ledger.balance_sheet(as_dataframe=False)

    # Income Statement / Sign adjustment (negative -> expenses / positive -> income)
    ic = myco_ledger.income_statement(as_dataframe=True, signs=True)
    return bs, bs_op, bs_f, ic

bs, bs_op, bs_f, ic = quickstart_2(reset_db=False)

# bss = pd.DataFrame(bs_f)