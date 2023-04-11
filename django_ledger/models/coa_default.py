"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

This is the base Chart of Accounts that has all the possible accounts that are useful for the preparation of the
Financial Statements. A user may choose to use the default CoA at the creation of each EntityModel but it is not
required. The default CoA is intended to provide a QuickStart solution for most use cases.

The Chart of Accounts is broadly bifurcated into 5 different Sections:
    1. Assets:
    2. Liabilities
    3. Shareholder's Equity
    4. Expenses
    5. Revenue

The Django Ledger Default Chart of Accounts must include the following fields:
    * Code - String
    * Role - A choice from any of the possible account roles (see django_ledger.roles module).
    * Balance Type - A CREDIT or DEBIT balance account setting.
    * Name - A human readable name.
    * Parent - The parent account of the AccountModel instance.

If the DEFAULT_CHART_OF_ACCOUNTS setting is present, the default CoA will be replace by such setting.

Default Chart of Accounts Table
===============================

======  ==========================  ==============  ===================================================  ========  ================
  code  role                        balance_type    name                                                   parent  root_group
======  ==========================  ==============  ===================================================  ========  ================
  1910  asset_adjustment            debit           Securities Unrealized Gains/Losses                             root_assets
  1920  asset_adjustment            debit           PPE Unrealized Gains/Losses                                    root_assets
  1010  asset_ca_cash               debit           Cash                                                           root_assets
  1200  asset_ca_inv                debit           Inventory                                                      root_assets
  1050  asset_ca_mkt_sec            debit           Short Term Investments                                         root_assets
  1300  asset_ca_prepaid            debit           Prepaid Expenses                                               root_assets
  1100  asset_ca_recv               debit           Accounts Receivable                                            root_assets
  1110  asset_ca_uncoll             credit          Uncollectibles                                                 root_assets
  1810  asset_ia                    debit           Goodwill                                                       root_assets
  1820  asset_ia                    debit           Intellectual Property                                          root_assets
  1830  asset_ia_accum_amort        credit          Less: Intangible Assets Accumulated Amortization               root_assets
  1520  asset_lti_land              debit           Land                                                           root_assets
  1510  asset_lti_notes             debit           Notes Receivable                                               root_assets
  1530  asset_lti_sec               debit           Securities                                                     root_assets
  1610  asset_ppe_build             debit           Buildings                                                      root_assets
  1611  asset_ppe_build_accum_depr  credit          Less: Buildings Accumulated Depreciation                       root_assets
  1630  asset_ppe_equip             debit           Equipment                                                      root_assets
  1631  asset_ppe_equip_accum_depr  credit          Less: Equipment Accumulated Depreciation                       root_assets
  1620  asset_ppe_plant             debit           Plant                                                          root_assets
  1640  asset_ppe_plant             debit           Vehicles                                                       root_assets
  1650  asset_ppe_plant             debit           Furniture & Fixtures                                           root_assets
  1621  asset_ppe_plant_depr        credit          Less: Plant Accumulated Depreciation                           root_assets
  1641  asset_ppe_plant_depr        credit          Less: Vehicles Accumulated Depreciation                        root_assets
  1651  asset_ppe_plant_depr        credit          Less: Furniture & Fixtures Accumulated Depreciation            root_assets
  3910  eq_adjustment               credit          Available for Sale                                             root_capital
  3920  eq_adjustment               credit          PPE Unrealized Gains/Losses                                    root_capital
  3010  eq_capital                  credit          Capital Account 1                                              root_capital
  3020  eq_capital                  credit          Capital Account 2                                              root_capital
  3030  eq_capital                  credit          Capital Account 3                                              root_capital
  3930  eq_dividends                debit           Dividends & Distributions                                      root_capital
  3110  eq_stock_common             credit          Common Stock                                                   root_capital
  3120  eq_stock_preferred          credit          Preferred Stock                                                root_capital
  5010  cogs_regular                debit           Cost of Goods Sold                                             root_cogs
  6075  ex_amortization             debit           Amortization Expense                                           root_expenses
  6070  ex_depreciation             debit           Depreciation Expense                                           root_expenses
  6130  ex_interest                 debit           Interest Expense                                               root_expenses
  6500  ex_other                    debit           Misc. Expense                                                  root_expenses
  6010  ex_regular                  debit           Advertising                                                    root_expenses
  6020  ex_regular                  debit           Amortization                                                   root_expenses
  6030  ex_regular                  debit           Auto Expense                                                   root_expenses
  6040  ex_regular                  debit           Bad Debt                                                       root_expenses
  6050  ex_regular                  debit           Bank Charges                                                   root_expenses
  6060  ex_regular                  debit           Commission Expense                                             root_expenses
  6080  ex_regular                  debit           Employee Benefits                                               root_expenses
  6090  ex_regular                  debit           Freight                                                        root_expenses
  6110  ex_regular                  debit           Gifts                                                          root_expenses
  6120  ex_regular                  debit           Insurance                                                      root_expenses
  6140  ex_regular                  debit           Professional Fees                                              root_expenses
  6150  ex_regular                  debit           License Expense                                                root_expenses
  6170  ex_regular                  debit           Maintenance Expense                                            root_expenses
  6180  ex_regular                  debit           Meals & Entertainment                                          root_expenses
  6190  ex_regular                  debit           Office Expense                                                  root_expenses
  6220  ex_regular                  debit           Printing                                                       root_expenses
  6230  ex_regular                  debit           Postage                                                        root_expenses
  6240  ex_regular                  debit           Rent                                                           root_expenses
  6250  ex_regular                  debit           Maintenance & Repairs                                          root_expenses
  6251  ex_regular                  debit           Maintenance                                                    root_expenses
  6252  ex_regular                  debit           Repairs                                                        root_expenses
  6253  ex_regular                  debit           HOA                                                            root_expenses
  6254  ex_regular                  debit           Snow Removal                                                   root_expenses
  6255  ex_regular                  debit           Lawn Care                                                      root_expenses
  6260  ex_regular                  debit           Salaries                                                       root_expenses
  6270  ex_regular                  debit           Supplies                                                       root_expenses
  6290  ex_regular                  debit           Utilities                                                      root_expenses
  6292  ex_regular                  debit           Sewer                                                          root_expenses
  6293  ex_regular                  debit           Gas                                                            root_expenses
  6294  ex_regular                  debit           Garbage                                                        root_expenses
  6295  ex_regular                  debit           Electricity                                                    root_expenses
  6300  ex_regular                  debit           Property Management                                            root_expenses
  6400  ex_regular                  debit           Vacancy                                                        root_expenses
  6210  ex_taxes                    debit           Payroll Taxes                                                  root_expenses
  6280  ex_taxes                    debit           Taxes                                                          root_expenses
  4040  in_gain_loss                credit          Capital Gain/Loss Income                                       root_income
  4030  in_interest                 credit          Interest Income                                                root_income
  4010  in_operational              credit          Sales Income                                                   root_income
  4050  in_other                    credit          Other Income                                                   root_income
  4020  in_passive                  credit          Investing Income                                               root_income
  2010  lia_cl_acc_payable          credit          Accounts Payable                                               root_liabilities
  2060  lia_cl_def_rev              credit          Deferred Revenues                                              root_liabilities
  2030  lia_cl_int_payable          credit          Interest Payable                                               root_liabilities
  2050  lia_cl_ltd_mat              credit          Current Maturities LT Debt                                     root_liabilities
  2070  lia_cl_other                credit          Other Payables                                                 root_liabilities
  2040  lia_cl_st_notes_payable     credit          Short-Term Notes Payable                                       root_liabilities
  2020  lia_cl_wages_payable        credit          Wages Payable                                                  root_liabilities
  2120  lia_ltl_bonds               credit          Bonds Payable                                                  root_liabilities
  2130  lia_ltl_mortgage            credit          Mortgage Payable                                               root_liabilities
  2110  lia_ltl_notes               credit          Long Term Notes Payable                                        root_liabilities
======  ==========================  ==============  ===================================================  ========  ================
"""

from itertools import groupby
from typing import Optional, Dict, List

from django_ledger.exceptions import DjangoLedgerConfigurationError
from django_ledger.io import roles, ROOT_ASSETS, ROOT_INCOME, ROOT_EXPENSES, ROOT_LIABILITIES, ROOT_CAPITAL, ROOT_COGS
from django_ledger.settings import DJANGO_LEDGER_DEFAULT_COA

# todo: include a function to use a user-defined CHART_OF_ACCOUNTS option.

DEFAULT_CHART_OF_ACCOUNTS = [

    # ---------# ASSETS START #---------#
    # CURRENT ASSETS  ------
    {'code': '1010', 'role': roles.ASSET_CA_CASH, 'balance_type': 'debit', 'name': 'Cash', 'parent': None},
    {'code': '1050', 'role': roles.ASSET_CA_MKT_SECURITIES, 'balance_type': 'debit', 'name': 'Short Term Investments',
     'parent': None},
    {'code': '1100', 'role': roles.ASSET_CA_RECEIVABLES, 'balance_type': 'debit', 'name': 'Accounts Receivable',
     'parent': None},
    {'code': '1110', 'role': roles.ASSET_CA_UNCOLLECTIBLES, 'balance_type': 'credit', 'name': 'Uncollectibles',
     'parent': None},
    {'code': '1200', 'role': roles.ASSET_CA_INVENTORY, 'balance_type': 'debit', 'name': 'Inventory', 'parent': None},
    {'code': '1300', 'role': roles.ASSET_CA_PREPAID, 'balance_type': 'debit', 'name': 'Prepaid Expenses',
     'parent': None},

    # LONG TERM INVESTMENTS ------
    {'code': '1510', 'role': roles.ASSET_LTI_NOTES_RECEIVABLE, 'balance_type': 'debit', 'name': 'Notes Receivable',
     'parent': None},
    {'code': '1520', 'role': roles.ASSET_LTI_LAND, 'balance_type': 'debit', 'name': 'Land', 'parent': None},
    {'code': '1530', 'role': roles.ASSET_LTI_SECURITIES, 'balance_type': 'debit', 'name': 'Securities', 'parent': None},

    # PPE ------
    {'code': '1610', 'role': roles.ASSET_PPE_BUILDINGS, 'balance_type': 'debit', 'name': 'Buildings', 'parent': None},
    {'code': '1611', 'role': roles.ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION, 'balance_type': 'credit',
     'name': 'Less: Buildings Accumulated Depreciation', 'parent': None},
    {'code': '1620', 'role': roles.ASSET_PPE_PLANT, 'balance_type': 'debit', 'name': 'Plant', 'parent': None},
    {'code': '1621', 'role': roles.ASSET_PPE_PLANT_ACCUM_DEPRECIATION, 'balance_type': 'credit',
     'name': 'Less: Plant Accumulated Depreciation', 'parent': None},
    {'code': '1630', 'role': roles.ASSET_PPE_EQUIPMENT, 'balance_type': 'debit', 'name': 'Equipment', 'parent': None},
    {'code': '1631', 'role': roles.ASSET_PPE_EQUIPMENT_ACCUM_DEPRECIATION, 'balance_type': 'credit',
     'name': 'Less: Equipment Accumulated Depreciation', 'parent': None},
    {'code': '1640', 'role': roles.ASSET_PPE_PLANT, 'balance_type': 'debit', 'name': 'Vehicles', 'parent': None},
    {'code': '1641', 'role': roles.ASSET_PPE_PLANT_ACCUM_DEPRECIATION, 'balance_type': 'credit',
     'name': 'Less: Vehicles Accumulated Depreciation', 'parent': None},
    {'code': '1650', 'role': roles.ASSET_PPE_PLANT, 'balance_type': 'debit', 'name': 'Furniture & Fixtures',
     'parent': None},
    {'code': '1651', 'role': roles.ASSET_PPE_PLANT_ACCUM_DEPRECIATION, 'balance_type': 'credit',
     'name': 'Less: Furniture & Fixtures Accumulated Depreciation', 'parent': None},

    # INTANGIBLE ASSETS ------
    {'code': '1810', 'role': roles.ASSET_INTANGIBLE_ASSETS, 'balance_type': 'debit', 'name': 'Goodwill',
     'parent': None},
    {'code': '1820', 'role': roles.ASSET_INTANGIBLE_ASSETS, 'balance_type': 'debit', 'name': 'Intellectual Property',
     'parent': None},
    {'code': '1830', 'role': roles.ASSET_INTANGIBLE_ASSETS_ACCUM_AMORTIZATION, 'balance_type': 'credit',
     'name': 'Less: Intangible Assets Accumulated Amortization', 'parent': '1820'},

    # ADJUSTMENTS ------
    {'code': '1910', 'role': roles.ASSET_ADJUSTMENTS, 'balance_type': 'debit',
     'name': 'Securities Unrealized Gains/Losses', 'parent': None},
    {'code': '1920', 'role': roles.ASSET_ADJUSTMENTS, 'balance_type': 'debit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': None},

    # ---------# ASSETS END #---------#

    # ---------# LIABILITIES START #---------#
    # CURRENT LIABILITIES ------
    {'code': '2010', 'role': roles.LIABILITY_CL_ACC_PAYABLE, 'balance_type': 'credit', 'name': 'Accounts Payable',
     'parent': None},
    {'code': '2020', 'role': roles.LIABILITY_CL_WAGES_PAYABLE, 'balance_type': 'credit', 'name': 'Wages Payable',
     'parent': None},
    {'code': '2030', 'role': roles.LIABILITY_CL_INTEREST_PAYABLE, 'balance_type': 'credit', 'name': 'Interest Payable',
     'parent': None},
    {'code': '2040', 'role': roles.LIABILITY_CL_ST_NOTES_PAYABLE, 'balance_type': 'credit',
     'name': 'Short-Term Notes Payable', 'parent': None},
    {'code': '2050', 'role': roles.LIABILITY_CL_LTD_MATURITIES, 'balance_type': 'credit',
     'name': 'Current Maturities LT Debt', 'parent': None},
    {'code': '2060', 'role': roles.LIABILITY_CL_DEFERRED_REVENUE, 'balance_type': 'credit', 'name': 'Deferred Revenues',
     'parent': None},
    {'code': '2070', 'role': roles.LIABILITY_CL_OTHER, 'balance_type': 'credit', 'name': 'Other Payables',
     'parent': None},

    # LIABILITIES ACCOUNTS ------
    {'code': '2110', 'role': roles.LIABILITY_LTL_NOTES_PAYABLE, 'balance_type': 'credit',
     'name': 'Long Term Notes Payable', 'parent': None},
    {'code': '2120', 'role': roles.LIABILITY_LTL_BONDS_PAYABLE, 'balance_type': 'credit', 'name': 'Bonds Payable',
     'parent': None},
    {'code': '2130', 'role': roles.LIABILITY_LTL_MORTGAGE_PAYABLE, 'balance_type': 'credit', 'name': 'Mortgage Payable',
     'parent': None},

    # ---------# LIABILITIES END #---------#

    # ---------# SHEREHOLDERS EQUITY START #---------#
    # CAPITAL ACCOUNTS ------
    {'code': '3010', 'role': roles.EQUITY_CAPITAL, 'balance_type': 'credit', 'name': 'Capital Account 1',
     'parent': None},
    {'code': '3020', 'role': roles.EQUITY_CAPITAL, 'balance_type': 'credit', 'name': 'Capital Account 2',
     'parent': None},
    {'code': '3030', 'role': roles.EQUITY_CAPITAL, 'balance_type': 'credit', 'name': 'Capital Account 3',
     'parent': None},

    {'code': '3110', 'role': roles.EQUITY_COMMON_STOCK, 'balance_type': 'credit', 'name': 'Common Stock',
     'parent': None},
    {'code': '3120', 'role': roles.EQUITY_PREFERRED_STOCK, 'balance_type': 'credit', 'name': 'Preferred Stock',
     'parent': None},

    {'code': '3910', 'role': roles.EQUITY_ADJUSTMENT, 'balance_type': 'credit', 'name': 'Available for Sale',
     'parent': None},
    {'code': '3920', 'role': roles.EQUITY_ADJUSTMENT, 'balance_type': 'credit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': None},

    {'code': '3930', 'role': roles.EQUITY_DIVIDENDS, 'balance_type': 'debit', 'name': 'Dividends & Distributions',
     'parent': None},

    # REVENUE ACCOUNTS ------
    {'code': '4010', 'role': roles.INCOME_OPERATIONAL, 'balance_type': 'credit', 'name': 'Sales Income',
     'parent': None},
    {'code': '4020', 'role': roles.INCOME_INVESTING, 'balance_type': 'credit', 'name': 'Investing Income',
     'parent': None},
    {'code': '4030', 'role': roles.INCOME_INTEREST, 'balance_type': 'credit', 'name': 'Interest Income',
     'parent': None},
    {'code': '4040', 'role': roles.INCOME_CAPITAL_GAIN_LOSS, 'balance_type': 'credit',
     'name': 'Capital Gain/Loss Income', 'parent': None},
    {'code': '4050', 'role': roles.INCOME_OTHER, 'balance_type': 'credit', 'name': 'Other Income', 'parent': None},

    # COGS ACCOUNTS ------
    {'code': '5010', 'role': roles.COGS, 'balance_type': 'debit', 'name': 'Cost of Goods Sold', 'parent': None},

    # EXPENSE ACCOUNTS ------
    {'code': '6010', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Advertising', 'parent': None},
    {'code': '6020', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Amortization',
     'parent': None},
    {'code': '6030', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Auto Expense',
     'parent': None},
    {'code': '6040', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Bad Debt', 'parent': None},
    {'code': '6050', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Bank Charges',
     'parent': None},
    {'code': '6060', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Commission Expense',
     'parent': None},
    {'code': '6080', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Employee Benefits',
     'parent': None},
    {'code': '6090', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Freight', 'parent': None},
    {'code': '6110', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Gifts', 'parent': None},
    {'code': '6120', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Insurance', 'parent': None},
    {'code': '6140', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Professional Fees',
     'parent': None},
    {'code': '6150', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'License Expense',
     'parent': None},
    {'code': '6170', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Maintenance Expense',
     'parent': None},
    {'code': '6180', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Meals & Entertainment',
     'parent': None},
    {'code': '6190', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Office Expense',
     'parent': None},
    {'code': '6220', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Printing', 'parent': None},
    {'code': '6230', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Postage', 'parent': None},
    {'code': '6240', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Rent', 'parent': None},
    {'code': '6250', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Maintenance & Repairs',
     'parent': None},
    {'code': '6251', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Maintenance', 'parent': None},
    {'code': '6252', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Repairs', 'parent': None},
    {'code': '6253', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'HOA', 'parent': None},
    {'code': '6254', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Snow Removal',
     'parent': None},
    {'code': '6255', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Lawn Care', 'parent': None},
    {'code': '6260', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Salaries', 'parent': None},
    {'code': '6270', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Supplies', 'parent': None},
    {'code': '6290', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Utilities', 'parent': None},
    {'code': '6292', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Sewer', 'parent': None},
    {'code': '6293', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Gas', 'parent': None},
    {'code': '6294', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Garbage', 'parent': None},
    {'code': '6295', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Electricity', 'parent': None},
    {'code': '6300', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Property Management',
     'parent': None},
    {'code': '6400', 'role': roles.EXPENSE_OPERATIONAL, 'balance_type': 'debit', 'name': 'Vacancy', 'parent': None},

    {'code': '6070', 'role': roles.EXPENSE_DEPRECIATION, 'balance_type': 'debit', 'name': 'Depreciation Expense',
     'parent': None},
    {'code': '6075', 'role': roles.EXPENSE_AMORTIZATION, 'balance_type': 'debit', 'name': 'Amortization Expense',
     'parent': None},
    {'code': '6130', 'role': roles.EXPENSE_INTEREST, 'balance_type': 'debit', 'name': 'Interest Expense',
     'parent': None},
    {'code': '6210', 'role': roles.EXPENSE_TAXES, 'balance_type': 'debit', 'name': 'Payroll Taxes', 'parent': None},
    {'code': '6280', 'role': roles.EXPENSE_TAXES, 'balance_type': 'debit', 'name': 'Taxes', 'parent': None},
    {'code': '6500', 'role': roles.EXPENSE_OTHER, 'balance_type': 'debit', 'name': 'Misc. Expense', 'parent': None}

]

PREFIX_MAP = {
    'in': ROOT_INCOME,
    'ex': ROOT_EXPENSES,
    'lia': ROOT_LIABILITIES,
    'eq': ROOT_CAPITAL,
    'asset': ROOT_ASSETS,
    'cogs': ROOT_COGS
}

for i in DEFAULT_CHART_OF_ACCOUNTS:
    i['root_group'] = PREFIX_MAP[i['role'].split('_')[0]]

DEFAULT_CHART_OF_ACCOUNTS.sort(key=lambda x: (x['root_group'], x['role'], x['code']))
CHART_OF_ACCOUNTS_ROOT_MAP = {
    k: list(v) for k, v in groupby(DEFAULT_CHART_OF_ACCOUNTS, key=lambda x: x['root_group'])
}


def verify_unique_code():
    """
    A function that verifies that there are no duplicate code in the Default CoA during the development and launch.
    """
    code_list = [i['code'] for i in DEFAULT_CHART_OF_ACCOUNTS]
    code_set = set(code_list)
    if not len(code_list) == len(code_set):
        raise DjangoLedgerConfigurationError('Default CoA is not unique.')


def get_default_coa() -> List[Dict]:
    if DJANGO_LEDGER_DEFAULT_COA is not None and isinstance(DJANGO_LEDGER_DEFAULT_COA, list):
        return DJANGO_LEDGER_DEFAULT_COA
    return DEFAULT_CHART_OF_ACCOUNTS


def get_default_coa_rst(default_coa: Optional[Dict] = None) -> str:
    """
    Converts the provided Chart of Account into restructuredText format.
    Parameters
    ----------
    default_coa:
        A dictionary of chart of accounts. Must follow the same keys as CHART_OF_ACCOUNTS.

    Returns
    -------
    str:
        The table in RestructuredText format.
    """
    try:
        from tabulate import tabulate
    except ModuleNotFoundError as e:
        raise DjangoLedgerConfigurationError(e.msg)
    if default_coa:
        return tabulate(default_coa, headers='keys', tablefmt='rst')
    return tabulate(get_default_coa(), headers='keys', tablefmt='rst')


verify_unique_code()
