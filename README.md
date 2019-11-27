# Django Ledger

### A bookkeeping & financial analysis engine for the Django Framework.

Django Ledger supports:

- Chart of Accounts.
- Financial Statements (Income Statement & Balance Sheets)
- Entities (LLC, Corps, etc.)
- General Ledgers
- Journal Entries & Transactions.
- Financial Activities Support (Operational/Financial/Investing)

Currently this project is under active development and is not recommended for production environments.
The author is working on incorporating the following functionality:

## Road Map
- Entity owners & user integration.
- Internationalization.
- Views & template tags.

## Quick Start

Django ledger currently does not ship with views as its main focus is to provide the
engine necessary to enable financially driven apps.

In order to start using Django Ledger you must create a Chart of Accounts (CoA).
Django Ledger comes with a default CoA ready to use or you could use your own. \
__Please user the following with caution if you are testing on an existing project!!!__
```python
from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel, make_account_active, get_acc_idx
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import create_coa_structure

# USE WITH CAUTION!!!!
reset_db = False

def quickstart(reset_db=reset_db):
    coa = None
    if reset_db:
        EntityModel.objects.filter(slug='my-co-inc').delete()
        ChartOfAccountModel.objects.filter(name='CoA QuickStart').delete()
        AccountModel.objects.all().delete()
        coa = create_coa_structure(coa_data=CHART_OF_ACCOUNTS,
                                   coa_name='CoA QuickStart',
                                   coa_desc='Django Ledger Default CoA')
    if not coa:
        coa, created = ChartOfAccountModel.objects.get_or_create(name='CoA QuickStart')
    make_account_active(coa, ['1010', '3010', '1610', '1611', '2110', '6253', '6290', '6070', '4020'])
    company, created = EntityModel.objects.get_or_create(slug='my-co-inc',
                                                         coa=coa,
                                                         name='MyCo Inc')
    ledger_id = 'my-co-ledger'  # auto generated if not provided
    myco_ledger, created = company.ledgers.get_or_create(slug=ledger_id, name='My Debug Ledger')
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
```

__Want to contribute? Don't hesitate to contact me.__