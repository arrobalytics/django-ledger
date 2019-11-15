from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel, make_account_active, get_acc_idx
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import create_coa_structure
from django_ledger.models.accounts import ACCOUNT_ROLES

RECREATE_COA = False

if RECREATE_COA:
    EntityModel.objects.all().delete()
    ChartOfAccountModel.objects.all().delete()
    AccountModel.objects.all().delete()
    create_coa_structure(coa_data=CHART_OF_ACCOUNTS, coa_name='CoA Default')

coa, created = ChartOfAccountModel.objects.get_or_create(slug='coa-default')
make_account_active(coa, ['1010', '3010', '1610', '2110', '6253', '4020'])

idx = get_acc_idx(coa, as_dataframe=0)

company, created = EntityModel.objects.get_or_create(slug='my-co-inc',
                                                     coa=coa,
                                                     name='MyCo Inc')

ledger_id = 'my-debug-ledger-66387'
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
    desc='Company funding to buy real estate.'
)

# Buy property
myco_ledger.tx_generic(
    amount=40000,
    start_date='2019-10-02',
    debit_acc='1610',
    credit_acc='1010',
    activity='inv',
    desc='Company funding to buy real estate.'
)

# Funding Company ---
myco_ledger.tx_generic(
    amount=80000,
    start_date='2019-10-02',
    debit_acc='1610',
    credit_acc='2110',
    activity='fin',
    desc='Company funding to buy real estate.'
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

# Balance Sheet & Income Statement ----
bs = myco_ledger.balance_sheet(as_dataframe=True)
ic = myco_ledger.income_statement(as_dataframe=True, signs=True)

myco_ledger.get_coa()