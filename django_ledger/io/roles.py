"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

import sys
from itertools import chain
from typing import List, Set, Union

from django.utils.translation import gettext as _

from django_ledger.exceptions import InvalidRoleError

mod = sys.modules[__name__]

DEBIT = 'debit'
CREDIT = 'credit'

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

# Property, Plant & Equipment ---
ASSET_PPE_BUILDINGS = 'asset_ppe_build'
ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION = 'asset_ppe_build_accum_depr'
ASSET_PPE_EQUIPMENT = 'asset_ppe_equip'
ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION = 'asset_ppe_equip_accum_depr'
ASSET_PPE_PLANT = 'asset_ppe_plant'
ASSET_PPE_PLANT_ACCUM_DEPRECIATION = 'asset_ppe_plant_depr'

# Intangible Assets ---
ASSET_INTANGIBLE_ASSETS = 'asset_ia'
ASSET_INTANGIBLE_ASSETS_ACCUM_AMORTIZATION = 'asset_ia_accum_amort'

# Other Asset Adjustments ---
ASSET_ADJUSTMENTS = 'asset_adjustment'

# LIABILITIES ----

# Current Liabilities
LIABILITY_CL_ACC_PAYABLE = 'lia_cl_acc_payable'
LIABILITY_CL_CREDIT_LINE = 'lia_cl_credit_line'
LIABILITY_CL_WAGES_PAYABLE = 'lia_cl_wages_payable'
LIABILITY_CL_TAXES_PAYABLE = 'lia_cl_taxes_payable'
LIABILITY_CL_INTEREST_PAYABLE = 'lia_cl_int_payable'
LIABILITY_CL_ST_NOTES_PAYABLE = 'lia_cl_st_notes_payable'
LIABILITY_CL_LTD_MATURITIES = 'lia_cl_ltd_mat'
LIABILITY_CL_DEFERRED_REVENUE = 'lia_cl_def_rev'
LIABILITY_CL_OTHER = 'lia_cl_other'

# Long Term Liabilities ---
LIABILITY_LTL_NOTES_PAYABLE = 'lia_ltl_notes'
LIABILITY_LTL_BONDS_PAYABLE = 'lia_ltl_bonds'
LIABILITY_LTL_MORTGAGE_PAYABLE = 'lia_ltl_mortgage'

# EQUITY ----
EQUITY_CAPITAL = 'eq_capital'
EQUITY_CAPITAL_CONTRIBUTION = 'eq_capital_contribution'
EQUITY_CAPITAL_DISTRIBUTION = 'eq_capital_distribution'
EQUITY_ADJUSTMENT = 'eq_adjustment'
EQUITY_COMMON_STOCK = 'eq_stock_common'
EQUITY_PREFERRED_STOCK = 'eq_stock_preferred'
EQUITY_DIVIDENDS = 'eq_dividends'

INCOME_OPERATIONAL = 'in_operational'
INCOME_PASSIVE = 'in_passive'
INCOME_CAPITAL_GAIN_LOSS = 'in_gain_loss'
INCOME_INTEREST = 'in_interest'
INCOME_OTHER = 'in_other'

COGS_REGULAR = 'cogs_regular'
COGS_LABOR = 'cogs_labor'
COGS_SUBCONTRACT = 'cogs_subcontract'
COGS_MATERIALS = 'cogs_materials'
COGS_EQUIPMENT = 'cogs_equipment'
COGS_OTHER = 'cogs_other'

EXPENSE_OPERATIONAL = 'ex_regular'
EXPENSE_CAPITAL = 'ex_capital'
EXPENSE_DEPRECIATION = 'ex_depreciation'
EXPENSE_AMORTIZATION = 'ex_amortization'
EXPENSE_TAXES = 'ex_taxes'
EXPENSE_INTEREST_ST = 'ex_interest_st'
EXPENSE_INTEREST_LT = 'ex_interest'
EXPENSE_OTHER = 'ex_other'

# ------> ROLES ACCOUNT ROOT <----- #

ROOT_COA = 'root_coa'
ROOT_ASSETS = 'root_assets'
ROOT_LIABILITIES = 'root_liabilities'
ROOT_CAPITAL = 'root_capital'
ROOT_INCOME = 'root_income'
ROOT_COGS = 'root_cogs'
ROOT_EXPENSES = 'root_expenses'

ROOT_GROUP = [ROOT_COA, ROOT_ASSETS, ROOT_LIABILITIES, ROOT_CAPITAL, ROOT_INCOME, ROOT_COGS, ROOT_EXPENSES]
ROOT_GROUP_LEVEL_2 = [ROOT_ASSETS, ROOT_LIABILITIES, ROOT_CAPITAL, ROOT_INCOME, ROOT_COGS, ROOT_EXPENSES]
ROOT_GROUP_META = {
    ROOT_COA: {'code': '00000000', 'title': 'CoA Root Node', 'balance_type': DEBIT},
    ROOT_ASSETS: {'code': '01000000', 'title': 'Asset Accounts Root Node', 'balance_type': DEBIT},
    ROOT_LIABILITIES: {'code': '02000000', 'title': 'Liability Accounts Root Node', 'balance_type': CREDIT},
    ROOT_CAPITAL: {'code': '03000000', 'title': 'Capital Accounts Root Node', 'balance_type': CREDIT},
    ROOT_INCOME: {'code': '04000000', 'title': 'Income Accounts Root Node', 'balance_type': CREDIT},
    ROOT_COGS: {'code': '05000000', 'title': 'COGS Accounts Root Node', 'balance_type': DEBIT},
    ROOT_EXPENSES: {'code': '06000000', 'title': 'Expense Accounts Root Node', 'balance_type': DEBIT},
}
# ------> ROLE GROUPS <-------#

GROUP_ASSETS = list()
GROUP_ASSETS.append(ROOT_ASSETS)

# ASSET GROUPS...
GROUP_QUICK_ASSETS = [ASSET_CA_CASH, ASSET_CA_MKT_SECURITIES]
GROUP_ASSETS += GROUP_QUICK_ASSETS

GROUP_CURRENT_ASSETS = [
    ASSET_CA_CASH,
    ASSET_CA_MKT_SECURITIES,
    ASSET_CA_INVENTORY,
    ASSET_CA_RECEIVABLES,
    ASSET_CA_PREPAID,
    ASSET_CA_UNCOLLECTIBLES,
    ASSET_CA_OTHER,
]
GROUP_ASSETS += GROUP_CURRENT_ASSETS

GROUP_NON_CURRENT_ASSETS = [
    ASSET_LTI_NOTES_RECEIVABLE,
    ASSET_LTI_LAND,
    ASSET_LTI_SECURITIES,
    ASSET_PPE_BUILDINGS,
    ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
    ASSET_PPE_EQUIPMENT,
    ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION,
    ASSET_PPE_PLANT,
    ASSET_PPE_PLANT_ACCUM_DEPRECIATION,
    ASSET_INTANGIBLE_ASSETS,
    ASSET_INTANGIBLE_ASSETS_ACCUM_AMORTIZATION,
    ASSET_ADJUSTMENTS,
]

GROUP_ASSETS += GROUP_NON_CURRENT_ASSETS
GROUP_ASSETS = list(set(GROUP_ASSETS))

# LIABILITY GROUPS....
GROUP_LIABILITIES = list()
GROUP_LIABILITIES.append(ROOT_LIABILITIES)

GROUP_CURRENT_LIABILITIES = [
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_CREDIT_LINE,
    LIABILITY_CL_DEFERRED_REVENUE,
    LIABILITY_CL_INTEREST_PAYABLE,
    LIABILITY_CL_LTD_MATURITIES,
    LIABILITY_CL_OTHER,
    LIABILITY_CL_ST_NOTES_PAYABLE,
    LIABILITY_CL_WAGES_PAYABLE,
    LIABILITY_CL_TAXES_PAYABLE,
]
GROUP_LIABILITIES += GROUP_CURRENT_LIABILITIES

GROUP_LT_LIABILITIES = [
    LIABILITY_LTL_NOTES_PAYABLE,
    LIABILITY_LTL_BONDS_PAYABLE,
    LIABILITY_LTL_MORTGAGE_PAYABLE,
]
GROUP_LIABILITIES += GROUP_LT_LIABILITIES

GROUP_LIABILITIES = list(set(GROUP_LIABILITIES))

# CAPITAL/EQUITY...
GROUP_CAPITAL = [
    ROOT_CAPITAL,
    EQUITY_CAPITAL,
    EQUITY_COMMON_STOCK,
    EQUITY_PREFERRED_STOCK,
    EQUITY_DIVIDENDS,
    EQUITY_ADJUSTMENT,
]

GROUP_TRANSFERS = [
    ASSET_CA_CASH,
]

GROUP_DEBT_PAYMENT = [
    ASSET_CA_CASH,
    LIABILITY_CL_CREDIT_LINE,
    LIABILITY_LTL_NOTES_PAYABLE,
    LIABILITY_LTL_MORTGAGE_PAYABLE,
    EXPENSE_INTEREST_ST,
    EXPENSE_INTEREST_LT,
]

# GROUP INCOME....
GROUP_INCOME_OPERATING = [INCOME_OPERATIONAL]
GROUP_INCOME_PASSIVE = [INCOME_PASSIVE]
GROUP_INCOME_INTEREST = [INCOME_INTEREST]
GROUP_INCOME_CAPITAL_GAIN_LOSS = [INCOME_CAPITAL_GAIN_LOSS]
GROUP_INCOME_OTHER = [INCOME_OTHER]

GROUP_INCOME_NON_OPERATING = (
    GROUP_INCOME_PASSIVE + GROUP_INCOME_INTEREST + GROUP_INCOME_CAPITAL_GAIN_LOSS + GROUP_INCOME_OTHER
)

GROUP_INCOME = [
    ROOT_INCOME,
    *GROUP_INCOME_OPERATING,
    *GROUP_INCOME_PASSIVE,
    *GROUP_INCOME_INTEREST,
    *GROUP_INCOME_CAPITAL_GAIN_LOSS,
    *GROUP_INCOME_OTHER,
]

# GROUP COGS....
GROUP_COGS = [ROOT_COGS, COGS_REGULAR, COGS_LABOR, COGS_SUBCONTRACT, COGS_EQUIPMENT, COGS_MATERIALS, COGS_OTHER]

# GROUP EXPENSES....

GROUP_EXPENSE_OPERATING = [EXPENSE_OPERATIONAL]
GROUP_EXPENSE_INTEREST = [EXPENSE_INTEREST_ST, EXPENSE_INTEREST_LT]
GROUP_EXPENSE_TAXES = [EXPENSE_TAXES]
GROUP_EXPENSE_CAPITAL = [EXPENSE_CAPITAL]
GROUP_EXPENSE_DEP_AND_AMT = [EXPENSE_DEPRECIATION, EXPENSE_AMORTIZATION]
GROUP_EXPENSE_OTHER = [EXPENSE_OTHER]

GROUP_EXPENSES = [
    ROOT_EXPENSES,
    *GROUP_EXPENSE_OPERATING,
    *GROUP_EXPENSE_INTEREST,
    *GROUP_EXPENSE_TAXES,
    *GROUP_EXPENSE_CAPITAL,
    *GROUP_EXPENSE_DEP_AND_AMT,
    *GROUP_EXPENSE_OTHER,
]

GROUP_PPE_ACCUM_DEPRECIATION = [
    ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
    ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION,
    ASSET_PPE_PLANT_ACCUM_DEPRECIATION,
]

GROUP_INVOICE = [ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_DEFERRED_REVENUE]
GROUP_BILL = [ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_ACC_PAYABLE]

# ############# PROFIT & LOSS GROUPS ###############


# ---> OPERATING REV/EXP (usual & frequent) <---- #
GROUP_PNL_OPERATING_INCOME = GROUP_INCOME_OPERATING
GROUP_PNL_COGS = GROUP_COGS
GROUP_PNL_OPERATING_EXPENSES = GROUP_EXPENSE_OPERATING

# ---> OTHER REV/EXP (unusual OR infrequent) <---- #
GROUP_PNL_OTHER_INCOME = GROUP_INCOME_NON_OPERATING
GROUP_PNL_OTHER_EXPENSES = [
    EXPENSE_INTEREST_ST,
    EXPENSE_INTEREST_LT,
    EXPENSE_TAXES,
    EXPENSE_CAPITAL,
    EXPENSE_DEPRECIATION,
    EXPENSE_AMORTIZATION,
    EXPENSE_OTHER,
]

GROUP_PNL_GROSS_PROFIT = GROUP_INCOME_OPERATING + GROUP_COGS
GROUP_PNL_OPERATING_PROFIT = GROUP_PNL_GROSS_PROFIT + GROUP_EXPENSE_OPERATING

GROUP_PNL_NET_PROFIT = [
    *GROUP_PNL_OPERATING_INCOME,
    *GROUP_PNL_COGS,
    *GROUP_PNL_OPERATING_EXPENSES,
    *GROUP_PNL_OTHER_INCOME,
    *GROUP_PNL_OTHER_EXPENSES,
]

# backwards compatibility groups...
GROUP_EARNINGS = GROUP_PNL_NET_PROFIT
# todo: must add another role for Sales returns, Sales allowances, Sales discounts...
GROUP_NET_SALES = GROUP_PNL_OPERATING_INCOME
GROUP_GROSS_PROFIT = GROUP_PNL_GROSS_PROFIT
GROUP_NET_PROFIT = GROUP_PNL_NET_PROFIT

# --> EBITDA <----
GROUP_PNL_EBITDA = [*GROUP_PNL_OPERATING_INCOME, *GROUP_PNL_COGS, *GROUP_PNL_OPERATING_EXPENSES, *GROUP_EXPENSE_OTHER]


GROUP_EQUITY = GROUP_CAPITAL + GROUP_PNL_NET_PROFIT
GROUP_LIABILITIES_EQUITY = GROUP_LIABILITIES + GROUP_EQUITY

# ############# CASH FLOW STATEMENT GROUPS ############
GROUP_CFS_NET_INCOME = GROUP_PNL_NET_PROFIT

# ---> OPERATING ACTIVITIES (INDIRECT) <---- #
# Non-Cash/Non-Current...
GROUP_CFS_OP_DEPRECIATION_AMORTIZATION = [EXPENSE_DEPRECIATION, EXPENSE_AMORTIZATION]
GROUP_CFS_OP_INVESTMENT_GAINS = [INCOME_CAPITAL_GAIN_LOSS]

# Non-Cash/Current...
GROUP_CFS_OP_ACCOUNTS_RECEIVABLE = [ASSET_CA_RECEIVABLES]
GROUP_CFS_OP_INVENTORY = [ASSET_CA_INVENTORY]
GROUP_CFS_OP_ACCOUNTS_PAYABLE = [LIABILITY_CL_ACC_PAYABLE, LIABILITY_CL_CREDIT_LINE]
GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT = [ASSET_CA_PREPAID, ASSET_CA_UNCOLLECTIBLES, ASSET_CA_OTHER]
GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT = [
    LIABILITY_CL_WAGES_PAYABLE,
    LIABILITY_CL_INTEREST_PAYABLE,
    LIABILITY_CL_TAXES_PAYABLE,
    LIABILITY_CL_LTD_MATURITIES,
    LIABILITY_CL_DEFERRED_REVENUE,
    LIABILITY_CL_OTHER,
]

GROUP_CFS_OPERATING = list(
    chain.from_iterable(
        [
            GROUP_CFS_NET_INCOME,
            GROUP_CFS_OP_DEPRECIATION_AMORTIZATION,
            GROUP_CFS_OP_INVESTMENT_GAINS,
            GROUP_CFS_OP_ACCOUNTS_RECEIVABLE,
            GROUP_CFS_OP_INVENTORY,
            GROUP_CFS_OP_ACCOUNTS_PAYABLE,
            GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT,
            GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT,
        ]
    )
)

# ---> FINANCING ACTIVITIES <---- #
GROUP_CFS_FIN_ISSUING_EQUITY = [EQUITY_CAPITAL, EQUITY_COMMON_STOCK, EQUITY_PREFERRED_STOCK]
GROUP_CFS_FIN_DIVIDENDS = [EQUITY_DIVIDENDS]

GROUP_CFS_FIN_ST_DEBT_PAYMENTS = [
    LIABILITY_CL_ST_NOTES_PAYABLE,
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_CREDIT_LINE,
    EXPENSE_INTEREST_ST,
]
GROUP_CFS_FIN_LT_DEBT_PAYMENTS = [
    LIABILITY_LTL_NOTES_PAYABLE,
    LIABILITY_LTL_BONDS_PAYABLE,
    LIABILITY_LTL_MORTGAGE_PAYABLE,
    EXPENSE_INTEREST_LT,
]

GROUP_CFS_FINANCING = GROUP_CFS_FIN_ISSUING_EQUITY + GROUP_CFS_FIN_DIVIDENDS
GROUP_CFS_FINANCING += GROUP_CFS_FIN_ST_DEBT_PAYMENTS
GROUP_CFS_FINANCING += GROUP_CFS_FIN_LT_DEBT_PAYMENTS

# ---> INVESTING ACTIVITIES <---- #
# Purchase of Assets....
GROUP_CFS_INV_PURCHASE_OR_SALE_OF_PPE = [
    ASSET_PPE_BUILDINGS,
    ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
    ASSET_PPE_PLANT,
    ASSET_PPE_PLANT_ACCUM_DEPRECIATION,
    ASSET_PPE_EQUIPMENT,
    ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION,
    INCOME_CAPITAL_GAIN_LOSS,
]

GROUP_CFS_INV_LTD_OF_PPE = [
    LIABILITY_LTL_NOTES_PAYABLE,
    LIABILITY_LTL_MORTGAGE_PAYABLE,
    LIABILITY_LTL_BONDS_PAYABLE,
]

GROUP_CFS_INVESTING_PPE = GROUP_CFS_INV_PURCHASE_OR_SALE_OF_PPE + GROUP_CFS_INV_LTD_OF_PPE

# Purchase/Sell of Securities...
GROUP_CFS_INV_PURCHASE_OF_SECURITIES = [
    ASSET_CA_MKT_SECURITIES,
    ASSET_LTI_NOTES_RECEIVABLE,
    ASSET_LTI_SECURITIES,
    INCOME_INTEREST,
    INCOME_PASSIVE,
    INCOME_CAPITAL_GAIN_LOSS,
]

GROUP_CFS_INV_LTD_OF_SECURITIES = [LIABILITY_LTL_NOTES_PAYABLE, LIABILITY_LTL_BONDS_PAYABLE]
GROUP_CFS_INVESTING_SECURITIES = GROUP_CFS_INV_PURCHASE_OF_SECURITIES + GROUP_CFS_INV_LTD_OF_SECURITIES

GROUP_CFS_INVESTING = GROUP_CFS_INVESTING_PPE + GROUP_CFS_INVESTING_SECURITIES

# ---> INVESTING & FINANCING ACTIVITIES <---- #
GROUP_CFS_INVESTING_AND_FINANCING = GROUP_CFS_INVESTING + GROUP_CFS_FINANCING

BS_ASSET_ROLE = 'assets'
BS_LIABILITIES_ROLE = 'liabilities'
BS_EQUITY_ROLE = 'equity'

ACCOUNT_ROLE_CHOICES = [
    (
        BS_ASSET_ROLE.capitalize(),
        (
            # CURRENT ASSETS ----
            (ASSET_CA_CASH, _('Cash & Equivalent')),
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
            # PPE ...
            (ASSET_PPE_BUILDINGS, _('Buildings')),
            (ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION, _('Buildings - Accum. Depreciation')),
            (ASSET_PPE_PLANT, _('Plant')),
            (ASSET_PPE_PLANT_ACCUM_DEPRECIATION, _('Plant - Accum. Depreciation')),
            (ASSET_PPE_EQUIPMENT, _('Equipment')),
            (ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION, _('Equipment - Accum. Depreciation')),
            # Other Assets ...
            (ASSET_INTANGIBLE_ASSETS, _('Intangible Assets')),
            (ASSET_INTANGIBLE_ASSETS_ACCUM_AMORTIZATION, _('Intangible Assets - Accum. Amortization')),
            (ASSET_ADJUSTMENTS, _('Other Assets')),
        ),
    ),
    (
        BS_LIABILITIES_ROLE.capitalize(),
        (
            # CURRENT LIABILITIES ---
            (LIABILITY_CL_ACC_PAYABLE, _('Accounts Payable')),
            (LIABILITY_CL_CREDIT_LINE, _('Credit Line')),
            (LIABILITY_CL_WAGES_PAYABLE, _('Wages Payable')),
            (LIABILITY_CL_INTEREST_PAYABLE, _('Interest Payable')),
            (LIABILITY_CL_TAXES_PAYABLE, _('Taxes Payable')),
            (LIABILITY_CL_ST_NOTES_PAYABLE, _('Short Term Notes Payable')),
            (LIABILITY_CL_LTD_MATURITIES, _('Current Maturities of Long Tern Debt')),
            (LIABILITY_CL_DEFERRED_REVENUE, _('Deferred Revenue')),
            (LIABILITY_CL_OTHER, _('Other Liabilities')),
            # LONG TERM LIABILITIES ----
            (LIABILITY_LTL_NOTES_PAYABLE, _('Long Term Notes Payable')),
            (LIABILITY_LTL_BONDS_PAYABLE, _('Bonds Payable')),
            (LIABILITY_LTL_MORTGAGE_PAYABLE, _('Mortgage Payable')),
        ),
    ),
    (
        BS_EQUITY_ROLE.capitalize(),
        (
            # EQUITY ---
            (EQUITY_CAPITAL, _('Capital')),
            (EQUITY_COMMON_STOCK, _('Common Stock')),
            (EQUITY_PREFERRED_STOCK, _('Preferred Stock')),
            (EQUITY_ADJUSTMENT, _('Other Equity Adjustments')),
            (EQUITY_DIVIDENDS, _('Dividends & Distributions to Shareholders')),
            # INCOME ---
            (INCOME_OPERATIONAL, _('Operational Income')),
            (INCOME_PASSIVE, _('Investing/Passive Income')),
            (INCOME_INTEREST, _('Interest Income')),
            (INCOME_CAPITAL_GAIN_LOSS, _('Capital Gain/Loss Income')),
            (INCOME_OTHER, _('Other Income')),
            # COGS ----
            (COGS_REGULAR, _('Cost of Goods Sold - Regular')),
            (COGS_SUBCONTRACT, _('Cost of Goods Sold - Subcontract')),
            (COGS_LABOR, _('Cost of Goods Sold - Labor')),
            (COGS_MATERIALS, _('Cost of Goods Sold - Materials')),
            (COGS_EQUIPMENT, _('Cost of Goods Sold - Equipment')),
            (COGS_OTHER, _('Cost of Goods Sold - Other')),
            # EXPENSES ----
            (EXPENSE_OPERATIONAL, _('Regular Expense')),
            (EXPENSE_INTEREST_ST, _('Interest Expense - Short Term Debt')),
            (EXPENSE_INTEREST_LT, _('Interest Expense - Long Term Debt')),
            (EXPENSE_TAXES, _('Tax Expense')),
            (EXPENSE_CAPITAL, _('Capital Expense')),
            (EXPENSE_DEPRECIATION, _('Depreciation Expense')),
            (EXPENSE_AMORTIZATION, _('Amortization Expense')),
            (EXPENSE_OTHER, _('Other Expense')),
        ),
    ),
    (
        'Root',
        (
            (ROOT_COA, 'CoA Root Account'),
            (ROOT_ASSETS, 'Assets Root Account'),
            (ROOT_LIABILITIES, 'Liabilities Root Account'),
            (ROOT_CAPITAL, 'Capital Root Account'),
            (ROOT_INCOME, 'Income Root Account'),
            (ROOT_COGS, 'COGS Root Account'),
            (ROOT_EXPENSES, 'Expenses Root Account'),
        ),
    ),
]

ACCOUNT_ROLE_CHOICES_FOR_FORMS = [
    (
        'Asset',
        (
            # CURRENT ASSETS ----
            (ASSET_CA_CASH, _('Cash & Equivalent')),
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
            # PPE ...
            (ASSET_PPE_BUILDINGS, _('Buildings')),
            (ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION, _('Buildings - Accum. Depreciation')),
            (ASSET_PPE_PLANT, _('Plant')),
            (ASSET_PPE_PLANT_ACCUM_DEPRECIATION, _('Plant - Accum. Depreciation')),
            (ASSET_PPE_EQUIPMENT, _('Equipment')),
            (ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION, _('Equipment - Accum. Depreciation')),
            # Other Assets ...
            (ASSET_INTANGIBLE_ASSETS, _('Intangible Assets')),
            (ASSET_INTANGIBLE_ASSETS_ACCUM_AMORTIZATION, _('Intangible Assets - Accum. Amortization')),
            (ASSET_ADJUSTMENTS, _('Other Assets')),
        ),
    ),
    (
        'Liabilities',
        (
            # CURRENT LIABILITIES ---
            (LIABILITY_CL_ACC_PAYABLE, _('Accounts Payable')),
            (LIABILITY_CL_CREDIT_LINE, _('Credit Line')),
            (LIABILITY_CL_WAGES_PAYABLE, _('Wages Payable')),
            (LIABILITY_CL_INTEREST_PAYABLE, _('Interest Payable')),
            (LIABILITY_CL_TAXES_PAYABLE, _('Taxes Payable')),
            (LIABILITY_CL_ST_NOTES_PAYABLE, _('Short Term Notes Payable')),
            (LIABILITY_CL_LTD_MATURITIES, _('Current Maturities of Long Tern Debt')),
            (LIABILITY_CL_DEFERRED_REVENUE, _('Deferred Revenue')),
            (LIABILITY_CL_OTHER, _('Other Liabilities')),
            # LONG TERM LIABILITIES ----
            (LIABILITY_LTL_NOTES_PAYABLE, _('Long Term Notes Payable')),
            (LIABILITY_LTL_BONDS_PAYABLE, _('Bonds Payable')),
            (LIABILITY_LTL_MORTGAGE_PAYABLE, _('Mortgage Payable')),
        ),
    ),
    (
        'Capital',
        (
            # EQUITY ---
            (EQUITY_CAPITAL, _('Capital')),
            (EQUITY_COMMON_STOCK, _('Common Stock')),
            (EQUITY_PREFERRED_STOCK, _('Preferred Stock')),
            (EQUITY_ADJUSTMENT, _('Other Equity Adjustments')),
            (EQUITY_DIVIDENDS, _('Dividends & Distributions to Shareholders')),
        ),
    ),
    (
        'Income',
        (
            # INCOME ---
            (INCOME_OPERATIONAL, _('Operational Income')),
            (INCOME_PASSIVE, _('Investing/Passive Income')),
            (INCOME_INTEREST, _('Interest Income')),
            (INCOME_CAPITAL_GAIN_LOSS, _('Capital Gain/Loss Income')),
            (INCOME_OTHER, _('Other Income')),
        ),
    ),
    (
        'Cost of Goods Sold',
        (
            (COGS_REGULAR, _('Cost of Goods Sold - Regular')),
            (COGS_LABOR, _('Cost of Goods Sold - Labor')),
            (COGS_SUBCONTRACT, _('Cost of Goods Sold - Subcontract')),
            (COGS_MATERIALS, _('Cost of Goods Sold - Materials')),
            (COGS_EQUIPMENT, _('Cost of Goods Sold - Equipment')),
            (COGS_OTHER, _('Cost of Goods Sold - Other')),
        ),
    ),
    (
        'Expense',
        (
            # EXPENSES ----
            (EXPENSE_OPERATIONAL, _('Regular Expense')),
            (EXPENSE_INTEREST_ST, _('Interest Expense - Short Term Debt')),
            (EXPENSE_INTEREST_LT, _('Interest Expense - Long Term Debt')),
            (EXPENSE_TAXES, _('Tax Expense')),
            (EXPENSE_CAPITAL, _('Capital Expense')),
            (EXPENSE_DEPRECIATION, _('Depreciation Expense')),
            (EXPENSE_AMORTIZATION, _('Amortization Expense')),
            (EXPENSE_OTHER, _('Other Expense')),
        ),
    ),
]

ACCOUNT_CHOICES_NO_ROOT = [c for c in ACCOUNT_ROLE_CHOICES if c[0] != 'Root']

ROLES_ORDER_ASSETS = [a[0] for a in ACCOUNT_ROLE_CHOICES[0][1]]
ROLES_ORDER_LIABILITIES = [a[0] for a in ACCOUNT_ROLE_CHOICES[1][1]]
ROLES_ORDER_CAPITAL = [a[0] for a in ACCOUNT_ROLE_CHOICES[2][1]]
ROLES_ORDER_ALL = list(chain.from_iterable([ROLES_ORDER_ASSETS, ROLES_ORDER_LIABILITIES, ROLES_ORDER_CAPITAL]))

ACCOUNT_LIST_ROLE_ORDER = list(r[0] for r in chain.from_iterable([i[1] for i in ACCOUNT_CHOICES_NO_ROOT]))
ACCOUNT_LIST_ROLE_VERBOSE = {r[0]: r[1] for r in chain.from_iterable([i[1] for i in ACCOUNT_CHOICES_NO_ROOT])}

ROLE_TUPLES = sum([[(r[0].lower(), s[0]) for s in r[1]] for r in ACCOUNT_ROLE_CHOICES], list())
ROLE_DICT = dict([(t[0].lower(), [r[0] for r in t[1]]) for t in ACCOUNT_ROLE_CHOICES])
VALID_ROLES = [r[1] for r in ROLE_TUPLES]
BS_ROLES = dict((r[1], r[0]) for r in ROLE_TUPLES)

BS_BUCKETS = {'0': 'Root', '1': 'Asset', '2': 'Liability', '3': 'Capital', '4': 'Income', '5': 'COGS', '6': 'Expenses'}
BS_BUCKETS_ORDER = [v for _, v in BS_BUCKETS.items() if v != 'Root']

ROLES_VARS = locals().keys()
ROLES_DIRECTORY = dict()
ROLES_CATEGORIES = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS', 'EXPENSE']

for cat in ROLES_CATEGORIES:
    ROLES_DIRECTORY[cat] = [c for c in ROLES_VARS if c.split('_')[0] == cat]

ROLES_GROUPS = [g for g in ROLES_VARS if g.split('_')[0] == 'GROUP']

GROUPS_DIRECTORY = dict()
for group in ROLES_GROUPS:
    GROUPS_DIRECTORY[group] = getattr(mod, group)

GROUP_VERBOSE_NAME = {
    'GROUP_ASSETS': _('Assets'),
    'GROUP_BILL': _('Bill'),
    'GROUP_CAPITAL': _('Capital'),
    'GROUP_PNL_OPERATING_INCOME': _('Operating Income'),
    'GROUP_PNL_COGS': _('Cost of Goods Sold'),
    'GROUP_PNL_GROSS_PROFIT': _('Gross Profit'),
    'GROUP_PNL_OPERATING_EXPENSES': _('Operating Expenses'),
    'GROUP_PNL_OPERATING_PROFIT': _('Operating Profit'),
    'GROUP_PNL_OTHER_INCOME': _('Other Income'),
    'GROUP_PNL_OTHER_EXPENSES': _('Other Expenses'),
    'GROUP_PNL_NET_PROFIT': _('Net Profit'),
    'GROUP_PNL_EBITDA': _('EBITDA'),
    'GROUP_PPE_ACCUM_DEPRECIATION': _('PPE Accumulated Depreciation'),
    'GROUP_CFS_FINANCING': _('Financing Activities'),
    'GROUP_CFS_FIN_DIVIDENDS': _('Dividends'),
    'GROUP_CFS_FIN_ISSUING_EQUITY': _('Issuing Equity'),
    'GROUP_CFS_FIN_LT_DEBT_PAYMENTS': _('Long Term Debt Payments'),
    'GROUP_CFS_FIN_ST_DEBT_PAYMENTS': _('Short Term Debt Payments'),
    'GROUP_CFS_INVESTING': _('Investing Activities'),
    'GROUP_CFS_INVESTING_AND_FINANCING': _('Investing & Financing Activities'),
    'GROUP_CFS_INVESTING_PPE': _('Investing PPE'),
    'GROUP_CFS_INVESTING_SECURITIES': _('Investing Securities'),
    'GROUP_CFS_INV_LTD_OF_PPE': _('Long Term Debt of PPE'),
    'GROUP_CFS_INV_LTD_OF_SECURITIES': _('Long Term Debt of Securities'),
    'GROUP_CFS_INV_PURCHASE_OF_SECURITIES': _('Purchase of Securities'),
    'GROUP_CFS_INV_PURCHASE_OR_SALE_OF_PPE': _('Purchase or Sale of PPE'),
    'GROUP_CFS_NET_INCOME': _('Net Income'),
    'GROUP_CFS_OPERATING': _('Operating Activities'),
    'GROUP_CFS_OP_ACCOUNTS_PAYABLE': _('Accounts Payable Adjustment'),
    'GROUP_CFS_OP_ACCOUNTS_RECEIVABLE': _('Accounts Receivable Adjustment'),
    'GROUP_CFS_OP_DEPRECIATION_AMORTIZATION': _('Depreciation & Amortization Adjustment'),
    'GROUP_CFS_OP_INVENTORY': _('Inventory Adjustment'),
    'GROUP_CFS_OP_INVESTMENT_GAINS': _('Investment Gains Adjustment'),
    'GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT': _('Other Current Assets Adjustment'),
    'GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT': _('Other Current Liabilities Adjustment'),
    'GROUP_COGS': _('Cost of Goods Sold'),
    'GROUP_CURRENT_ASSETS': _('Current Assets'),
    'GROUP_CURRENT_LIABILITIES': _('Current Liabilities'),
    'GROUP_DEBT_PAYMENT': _('Debt Payment'),
    'GROUP_EQUITY': _('Equity'),
    'GROUP_EXPENSES': _('Expenses'),
    'GROUP_EXPENSE_CAPITAL': _('Capital Expense'),
    'GROUP_EXPENSE_DEP_AND_AMT': _('Depreciation & Amortization Expense'),
    'GROUP_EXPENSE_INTEREST': _('Interest Expense'),
    'GROUP_EXPENSE_OPERATING': _('Operating Expense'),
    'GROUP_EXPENSE_OTHER': _('Other Expense'),
    'GROUP_EXPENSE_TAXES': _('Tax Expense'),
    'GROUP_INCOME': _('Income'),
    'GROUP_INCOME_CAPITAL_GAIN_LOSS': _('Capital Gain/Loss Income'),
    'GROUP_INCOME_INTEREST': _('Interest Income'),
    'GROUP_INCOME_NON_OPERATING': _('Non-Operating Income'),
    'GROUP_INCOME_OPERATING': _('Operating Income'),
    'GROUP_INCOME_OTHER': _('Other Income'),
    'GROUP_INCOME_PASSIVE': _('Passive Income'),
    'GROUP_INVOICE': _('Invoice'),
    'GROUP_LIABILITIES': _('Liabilities'),
    'GROUP_LIABILITIES_EQUITY': _('Liabilities & Equity'),
    'GROUP_LT_LIABILITIES': _('Long-Term Liabilities'),
    'GROUP_NON_CURRENT_ASSETS': _('Non-Current Assets'),
    'GROUP_QUICK_ASSETS': _('Quick Assets'),
    'GROUP_TRANSFERS': _('Transfers'),
}


def validate_roles(roles: Union[str, List[str]], raise_exception: bool = True) -> Set[str]:
    """
    Validates a given role identifier against the valid role available.
    Parameters
    ----------
    roles: str or list
        The role or list of roles to validate.
    raise_exception: bool
        Raises InvalidRoleError if any of the roles provided if not valid.

    Returns
    -------
    set
        A set of the valid roles.
    """
    if isinstance(roles, str):
        roles = list()
        roles.append(roles)

    for r in roles:
        if r not in VALID_ROLES:
            if raise_exception:
                raise InvalidRoleError('{rls}) is invalid. Choices are {ch}'.format(ch=', '.join(VALID_ROLES), rls=r))
    return set(roles)


VALID_PARENTS = {
    ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION: [ASSET_PPE_BUILDINGS],
    ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION: [ASSET_PPE_EQUIPMENT],
    ASSET_PPE_PLANT_ACCUM_DEPRECIATION: [ASSET_PPE_PLANT],
}
