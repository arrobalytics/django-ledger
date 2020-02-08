from django_ledger.io import roles

CHART_OF_ACCOUNTS = [

    # ---------# ASSETS START #---------#
    # CURRENT ASSETS  ------
    {'code': '1010', 'role': roles.ASSET_CA_CASH, 'balance_type': 'debit', 'name': 'Cash', 'parent': None},
    {'code': '1050', 'role': roles.ASSET_CA_MKT_SECURITIES, 'balance_type': 'debit', 'name': 'Short Term Investments',
     'parent': None},
    {'code': '1100', 'role': roles.ASSET_CA_RECEIVABLES, 'balance_type': 'debit', 'name': 'Accounts Receivable',
     'parent': None},
    {'code': '1101', 'role': roles.ASSET_CA_UNCOLLECTIBLES, 'balance_type': 'credit', 'name': 'Uncollectibles',
     'parent': None},
    {'code': '1200', 'role': roles.ASSET_CA_INVENTORY, 'balance_type': 'debit', 'name': 'Inventory', 'parent': None},
    {'code': '1300', 'role': roles.ASSET_CA_PREPAID, 'balance_type': 'debit', 'name': 'Prepaid Expenses',
     'parent': None},

    # LONG TERM IMVESTMENTS ------
    {'code': '1510', 'role': roles.ASSET_LTI_NOTES_RECEIVABLE, 'balance_type': 'debit', 'name': 'Notes Receivable',
     'parent': None},
    {'code': '1520', 'role': roles.ASSET_LTI_LAND, 'balance_type': 'debit', 'name': 'Land', 'parent': None},
    {'code': '1530', 'role': roles.ASSET_LTI_SECURITIES, 'balance_type': 'debit', 'name': 'Securities', 'parent': None},

    # PPE ------
    {'code': '1610', 'role': roles.ASSET_PPE, 'balance_type': 'debit', 'name': 'Buildings', 'parent': None},
    {'code': '1611', 'role': roles.ASSET_PPE, 'balance_type': 'credit',
     'name': 'Less: Buildings Accumulated Depreciation', 'parent': None},
    {'code': '1620', 'role': roles.ASSET_PPE, 'balance_type': 'debit', 'name': 'Plant', 'parent': None},
    {'code': '1621', 'role': roles.ASSET_PPE, 'balance_type': 'credit',
     'name': 'Less: Plant Accumulated Depreciation', 'parent': None},
    {'code': '1630', 'role': roles.ASSET_PPE, 'balance_type': 'debit', 'name': 'Equipment', 'parent': None},
    {'code': '1631', 'role': roles.ASSET_PPE, 'balance_type': 'credit',
     'name': 'Less: Equipment Accumulated Depreciation', 'parent': None},
    {'code': '1640', 'role': roles.ASSET_PPE, 'balance_type': 'debit', 'name': 'Vehicles', 'parent': None},
    {'code': '1641', 'role': roles.ASSET_PPE, 'balance_type': 'credit',
     'name': 'Less: Vehicles Accumulated Depreciation', 'parent': None},
    {'code': '1650', 'role': roles.ASSET_PPE, 'balance_type': 'debit', 'name': 'Furniture & Fixtures',
     'parent': None},
    {'code': '1651', 'role': roles.ASSET_PPE, 'balance_type': 'credit',
     'name': 'Less: Furniture & Fixtures Accumulated Depreciation', 'parent': None},

    # INTANGIBLE ASSETS ------
    {'code': '1810', 'role': roles.ASSET_INTANGIBLE_ASSETS, 'balance_type': 'debit', 'name': 'Goodwill',
     'parent': None},
    {'code': '1820', 'role': roles.ASSET_INTANGIBLE_ASSETS, 'balance_type': 'debit', 'name': 'Intellectual Property',
     'parent': None},

    # ADJUSTMENTS ------
    {'code': '1910', 'role': roles.ASSET_ADJUSTMENTS, 'balance_type': 'debit',
     'name': 'Securities Unrealized Gains/Losses',
     'parent': None},
    {'code': '1920', 'role': roles.ASSET_ADJUSTMENTS, 'balance_type': 'debit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': None},

    # ---------# ASSETS END #---------#

    # ---------# LIABILITIES START #---------#
    # CURRENT LIABILITIES ------
    {'code': '2010', 'role': roles.LIABILITY_CL_ACC_PAYABLE, 'balance_type': 'credit', 'name': 'Accounts Payable',
     'parent': None},
    {'code': '2020', 'role': roles.LIABILITY_CL_WAGES_PAYABLE, 'balance_type': 'credit', 'name': 'Wages Payable',
     'parent': None},
    {'code': '2030', 'role': roles.LIABILITY_CL_INT_PAYABLE, 'balance_type': 'credit', 'name': 'Interest Payable',
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
     'name': 'Long Term Notes Payable',
     'parent': None},
    {'code': '2120', 'role': roles.LIABILITY_LTL_BONDS_PAYABLE, 'balance_type': 'credit', 'name': 'Bonds Payable',
     'parent': None},
    {'code': '2130', 'role': roles.LIABILITY_LTL_MORTAGE_PAYABLE, 'balance_type': 'credit', 'name': 'Mortgage Payable',
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

    {'code': '3910', 'role': roles.EQUITY_ADJUSTMENT, 'balance_type': 'credit', 'name': 'Available for Sale', 'parent': None},
    {'code': '3920', 'role': roles.EQUITY_ADJUSTMENT, 'balance_type': 'credit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': None},

    # REVENUE ACCOUNTS ------
    {'code': '4010', 'role': roles.INCOME_SALES, 'balance_type': 'credit', 'name': 'Sales Income', 'parent': None},
    {'code': '4020', 'role': roles.INCOME_PASSIVE, 'balance_type': 'credit', 'name': 'Passive Income',
     'parent': None},
    {'code': '4030', 'role': roles.INCOME_OTHER, 'balance_type': 'credit', 'name': 'Property Sales Income',
     'parent': None},

    # COGS ACCOUNTS ------
    {'code': '5010', 'role': roles.COGS, 'balance_type': 'debit', 'name': 'Cost of Goods Sold', 'parent': None},

    # EXPENSE ACCOUNTS ------
    {'code': '6010', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Advertising', 'parent': None},
    {'code': '6020', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Amortization', 'parent': None},
    {'code': '6030', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Auto Expense', 'parent': None},
    {'code': '6040', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Bad Debt', 'parent': None},
    {'code': '6050', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Bank Charges', 'parent': None},
    {'code': '6060', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Commission Expense',
     'parent': None},
    {'code': '6070', 'role': roles.EXPENSE_CAPITAL, 'balance_type': 'debit', 'name': 'Depreciation Expense',
     'parent': None},
    {'code': '6080', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Employee Benefits',
     'parent': None},
    {'code': '6090', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Freight', 'parent': None},
    {'code': '6110', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Gifts', 'parent': None},
    {'code': '6120', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Insurance', 'parent': None},
    {'code': '6130', 'role': roles.EXPENSE_INTEREST, 'balance_type': 'debit', 'name': 'Interest Expense',
     'parent': None},
    {'code': '6140', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Professional Fees',
     'parent': None},
    {'code': '6150', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'License Expense',
     'parent': None},
    {'code': '6170', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Maintenance Expense',
     'parent': None},
    {'code': '6180', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Meals & Entertainment',
     'parent': None},
    {'code': '6190', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Office Expense', 'parent': None},
    {'code': '6210', 'role': roles.EXPENSE_TAXES, 'balance_type': 'debit', 'name': 'Payroll Taxes',
     'parent': None},
    {'code': '6220', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Printing', 'parent': None},
    {'code': '6230', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Postage', 'parent': None},
    {'code': '6240', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Rent', 'parent': None},

    {'code': '6250', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Maintenance & Repairs',
     'parent': None},
    {'code': '6251', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Maintenance', 'parent': None},
    {'code': '6252', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Repairs', 'parent': None},
    {'code': '6253', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'HOA', 'parent': None},
    {'code': '6254', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Snow Removal', 'parent': None},
    {'code': '6255', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Lawn Care', 'parent': None},

    {'code': '6260', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Salaries', 'parent': None},
    {'code': '6270', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Supplies', 'parent': None},
    {'code': '6280', 'role': roles.EXPENSE_TAXES, 'balance_type': 'debit', 'name': 'Taxes', 'parent': None},

    {'code': '6290', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Utilities', 'parent': None},
    {'code': '6292', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Sewer', 'parent': None},
    {'code': '6293', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Gas', 'parent': None},
    {'code': '6294', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Garbage', 'parent': None},
    {'code': '6295', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Electricity', 'parent': None},

    {'code': '6300', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Property Management',
     'parent': None},
    {'code': '6400', 'role': roles.EXPENSE_OP, 'balance_type': 'debit', 'name': 'Vacancy', 'parent': None},

    # MISC REVENUE ACCOUNTS ------
    {'code': '7010', 'role': roles.INCOME_OTHER, 'balance_type': 'credit', 'name': 'Misc. Revenue',
     'parent': None},

    # MISC EXPENSE ACCOUNTS ------
    {'code': '7510', 'role': roles.EXPENSE_OTHER, 'balance_type': 'debit', 'name': 'Misc. Expense',
     'parent': None},

    # ---------# SHAREHOLDER'S EQUITY END #---------#

]
