from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# --- ASSET ROLES ----
# Current Assets ---
ASSET_CA_CASH = 'asset_ca_cash'
ASSET_CA_MKT_SECURITIES = 'asset_ca_mkt_sec'
ASSET_CA_RECEIVABLES = 'asset_ca_recv'
ASSET_CA_INVENTORY = 'asset_ca_inv'
ASSET_CA_UNCOLLECTIBLES = 'asset_ca_uncoll'
ASSET_CA_PREPAID = 'asset_ca_prepaid'
ASSET_CA_OTHER = 'asset_ca_other'

# Long Term Investments ---
ASSET_LTI_NOTES_RECEIVABLE = 'asset_lti_notes'
ASSET_LTI_LAND = 'asset_lti_land'
ASSET_LTI_SECURITIES = 'asset_lti_sec'

# Property, Plat & Equipment ---
ASSET_PPE = 'asset_ppe'

# Intangible Assets ---
ASSET_INTANGIBLE_ASSETS = 'asset_ia'

# Other Asset Adjustments ---
ASSET_ADJUSTMENTS = 'asset_adjustment'

# LIABILITIES ----

# Current Liabilities
LIABILITY_CL_ACC_PAYABLE = 'lia_cl_acc_pay'
LIABILITY_CL_WAGES_PAYABLE = 'lia_cl_wage_pay'
LIABILITY_CL_INT_PAYABLE = 'lia_cl_wage_pay'
LIABILITY_CL_ST_NOTES_PAYABLE = 'lia_cl_st_notes_payable'
LIABILITY_CL_LTD_MATURITIES = 'lia_cl_ltd_mat'
LIABILITY_CL_DEFERRED_REVENUE = 'lia_cl_def_rev'
LIABILITY_CL_OTHER = 'lia_cl_other'

# Long Term Liabilities ---
LIABILITY_LTL_NOTES_PAYABLE = 'lia_ltl_notes'
LIABILITY_LTL_BONDS_PAYABLE = 'lia_ltl_bonds'
LIABILITY_LTL_MORTAGE_PAYABLE = 'lia_ltl_mortgage'

# EQUITY ----
EQUITY_CAPITAL = 'eq_capital'
EQUITY_ADJUSTMENT = 'eq_adjustment'
EQUITY_COMMON_STOCK = 'eq_stock_c'
EQUITY_PREFERRED_STOCK = 'eq_stock_p'

INCOME_SALES = 'in_sales'
INCOME_PASSIVE = 'in_pass'
INCOME_OTHER = 'in_other'

COGS = 'ex_cogs'

EXPENSE_OP = 'ex_op'
EXPENSE_CAPITAL = 'ex_cap'
EXPENSE_TAXES = 'ex_taxes'
EXPENSE_INTEREST = 'ex_interest'
EXPENSE_OTHER = 'ex_other'

# ------> ROLE GROUPS <-------#
GROUP_QUICK_ASSETS = [
    ASSET_CA_CASH,
    ASSET_CA_MKT_SECURITIES
]

ROLES_CURRENT_ASSETS = [
    ASSET_CA_CASH,
    ASSET_CA_MKT_SECURITIES,
    ASSET_CA_INVENTORY,
    ASSET_CA_RECEIVABLES,
    ASSET_CA_PREPAID,
    ASSET_CA_OTHER
]

ROLES_ASSETS = ROLES_CURRENT_ASSETS + [
    ASSET_LTI_NOTES_RECEIVABLE,
    ASSET_LTI_LAND,
    ASSET_LTI_SECURITIES,
    ASSET_PPE,
    ASSET_INTANGIBLE_ASSETS,
    ASSET_ADJUSTMENTS
]

ROLES_CURRENT_LIABILITIES = [
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_DEFERRED_REVENUE,
    LIABILITY_CL_INT_PAYABLE,
    LIABILITY_CL_LTD_MATURITIES,
    LIABILITY_CL_OTHER,
    LIABILITY_CL_ST_NOTES_PAYABLE,
    LIABILITY_CL_WAGES_PAYABLE
]

ROLES_LIABILITIES = ROLES_CURRENT_LIABILITIES + [
    LIABILITY_LTL_NOTES_PAYABLE,
    LIABILITY_LTL_BONDS_PAYABLE,
    LIABILITY_LTL_MORTAGE_PAYABLE,
]

ROLES_CAPITAL = [
    EQUITY_CAPITAL,
    EQUITY_COMMON_STOCK,
    EQUITY_PREFERRED_STOCK,
    EQUITY_ADJUSTMENT
]

ROLES_INCOME = [
    INCOME_SALES,
    INCOME_PASSIVE,
    INCOME_OTHER,
]

ROLES_EXPENSES = [
    COGS,
    EXPENSE_OP,
    EXPENSE_INTEREST,
    EXPENSE_TAXES,
    EXPENSE_CAPITAL,
    EXPENSE_OTHER
]

ROLES_NET_PROFIT = [
    INCOME_SALES,
    INCOME_PASSIVE,
    INCOME_OTHER,
    COGS,
]

ROLES_GROSS_PROFIT = [
    INCOME_SALES,
    COGS
]

ROLES_NET_SALES = [
    INCOME_SALES,
    INCOME_PASSIVE
]

ROLES_EARNINGS = ROLES_INCOME + ROLES_EXPENSES

ACCOUNT_ROLES = [
    ('Assets', (
        # CURRENT ASSETS ----
        (ASSET_CA_CASH, _('Current Asset')),
        (ASSET_CA_MKT_SECURITIES, _('Marketable Securities')),
        (ASSET_CA_RECEIVABLES, _('Receivables')),
        (ASSET_CA_INVENTORY, _('Inventory')),
        (ASSET_CA_UNCOLLECTIBLES, _('Uncollectibles')),
        (ASSET_CA_PREPAID, _('Prepaid')),
        (ASSET_CA_OTHER, _('Other Liquid Assets')),

        # LONG TERM INVESTMENTS ---
        (ASSET_LTI_NOTES_RECEIVABLE, _('Notes Receivable')),
        (ASSET_LTI_LAND, _('Land')),
        (ASSET_LTI_SECURITIES, _('Securities')),

        (ASSET_PPE, _('Property Plant & Equipment')),
        (ASSET_INTANGIBLE_ASSETS, _('Intangible Assets')),
        (ASSET_ADJUSTMENTS, _('Other Assets')),
    )
     ),
    ('Liabilities', (

        # CURRENT LIABILITIES ---
        (LIABILITY_CL_ACC_PAYABLE, _('Accounts Payable')),
        (LIABILITY_CL_WAGES_PAYABLE, _('Wages Payable')),
        (LIABILITY_CL_INT_PAYABLE, _('Interest Payable')),
        (LIABILITY_CL_ST_NOTES_PAYABLE, _('Notes Payable')),
        (LIABILITY_CL_LTD_MATURITIES, _('Current Maturities of Long Tern Debt')),
        (LIABILITY_CL_DEFERRED_REVENUE, _('Deferred Revenue')),
        (LIABILITY_CL_OTHER, _('Other Liabilities')),

        # LONG TERM LIABILITIES ----
        (LIABILITY_LTL_NOTES_PAYABLE, _('Notes Payable')),
        (LIABILITY_LTL_BONDS_PAYABLE, _('Bonds Payable')),
        (LIABILITY_LTL_MORTAGE_PAYABLE, _('Mortgage Payable')),

    )
     ),
    ('Equity', (

        # EQUITY ---
        (EQUITY_CAPITAL, _('Capital')),
        (EQUITY_COMMON_STOCK, _('Common Stock')),
        (EQUITY_PREFERRED_STOCK, _('Preferred Stock')),
        (EQUITY_ADJUSTMENT, _('Other Equity Adjustments')),

        # INCOME ---
        (INCOME_SALES, _('Sales Income')),
        (INCOME_PASSIVE, _('Passive Income')),
        (INCOME_OTHER, _('Other Income')),

        # COGS ----
        (COGS, _('Cost of Goods Sold')),

        # EXPENSES ----
        (EXPENSE_OP, _('Operational Expense')),
        (EXPENSE_INTEREST, _('Interest Expense')),
        (EXPENSE_TAXES, _('Tax Expense')),
        (EXPENSE_CAPITAL, _('Capital Expense')),
        (EXPENSE_OTHER, _('Other Expense')),
    )
     )
]

ROLE_TUPLES = sum([[(r[0].lower(), s[0]) for s in r[1]] for r in ACCOUNT_ROLES], list())
ROLE_DICT = dict([(t[0].lower(), [r[0] for r in t[1]]) for t in ACCOUNT_ROLES])
VALID_ROLES = [r[1] for r in ROLE_TUPLES]
BS_ROLES = dict([(r[1], r[0]) for r in ROLE_TUPLES])


def validate_roles(roles):
    if roles:
        if isinstance(roles, str):
            roles = [roles]
        for r in roles:
            if r not in VALID_ROLES:
                raise ValidationError('{roles}) is invalid. Choices are {ch}'.format(ch=', '.join(VALID_ROLES),
                                                                                     roles=r))
    return roles


ROLES_DIRECTORY = dict()
LOCALS = locals().keys()
ROLES_CATEGORIES = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS', 'EXPENSE']
for cat in ROLES_CATEGORIES:
    ROLES_DIRECTORY[cat] = [c for c in LOCALS if c.split('_')[0] == cat]
