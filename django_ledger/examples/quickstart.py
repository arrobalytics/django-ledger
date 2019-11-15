from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel, make_account_active, get_acc_idx
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import create_coa_structure

RECREATE_COA = False
if RECREATE_COA:
    AccountModel.objects.all().delete()
    ChartOfAccountModel.objects.all().delete()
    EntityModel.objects.all().delete()
    create_coa_structure(coa_data=CHART_OF_ACCOUNTS, coa_name='CoA Default')

coa = ChartOfAccountModel.objects.get(slug='coa-default')
make_account_active(coa, ['1010', '1020'])

idx = get_acc_idx(coa, as_dataframe=0)

company, created = EntityModel.objects.get_or_create(slug='edma',
                                                     coa=coa,
                                                     name='EDMA Group Inc')
company.general_ledger.all()

ledger_id = 'my-debug-ledger-66387'
edma_ledger, created = company.general_ledger.get_or_create(slug=ledger_id)
# edma_ledger, created = company.general_ledger.get_or_create(name='My Debug Ledger')

edma_ledger.journal_entry.all().delete()
# Company Funding
funding =200000
edma_ledger.tx_generic(
    amount=funding,
    start_date='2019-10-02',
    debit_acc='1010',
    credit_acc='3010',
    activity='other',
    desc='Company funding to buy real estate.'
)

# Buy property
edma_ledger.tx_generic(
    amount=40000,
    start_date='2019-10-02',
    debit_acc='1610',
    credit_acc='1010',
    activity='inv',
    desc='Company funding to buy real estate.'
)

edma_ledger.tx_generic(
    amount=80000,
    start_date='2019-10-02',
    debit_acc='1610',
    credit_acc='2110',
    activity='fin',
    desc='Company funding to buy real estate.'
)

bs = edma_ledger.balance_sheet(as_dataframe=True)
ic = edma_ledger.income_statement(as_dataframe=True)

