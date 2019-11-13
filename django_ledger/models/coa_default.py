CHART_OF_ACCOUNTS = [

    # ---------# ASSETS START #---------#
    # CURRENT ASSET  ------
    {'code': 1000, 'role': 'ca', 'balance_type': 'debit', 'name': 'CURRENT ASSETS', 'parent': 1000},
    {'code': 1010, 'role': 'ca', 'balance_type': 'debit', 'name': 'Cash', 'parent': 1000},
    {'code': 1050, 'role': 'ca', 'balance_type': 'debit', 'name': 'Short Term Investments', 'parent': 1000},
    {'code': 1100, 'role': 'ca', 'balance_type': 'debit', 'name': 'Accounts Receivable', 'parent': 1000},
    {'code': 1101, 'role': 'ca', 'balance_type': 'credit', 'name': 'Uncollectibles', 'parent': 1000},
    {'code': 1200, 'role': 'ca', 'balance_type': 'debit', 'name': 'Inventory', 'parent': 1000},
    {'code': 1300, 'role': 'ca', 'balance_type': 'debit', 'name': 'Prepaid Expenses', 'parent': 1000},

    # LONG TERM IMVESTMENTS ------
    {'code': 1500, 'role': 'lti', 'balance_type': 'debit', 'name': 'LONG TERM INVESTMENTS', 'parent': 1500},
    {'code': 1510, 'role': 'lti', 'balance_type': 'debit', 'name': 'Notes Receivable', 'parent': 1500},
    {'code': 1520, 'role': 'lti', 'balance_type': 'debit', 'name': 'Land', 'parent': 1500},
    {'code': 1530, 'role': 'lti', 'balance_type': 'debit', 'name': 'Securities', 'parent': 1500},

    # PPE ------
    {'code': 1600, 'role': 'ppe', 'balance_type': 'debit', 'name': 'PPE', 'parent': 1600},
    {'code': 1610, 'role': 'ppe', 'balance_type': 'debit', 'name': 'Buildings', 'parent': 1600},
    {'code': 1611, 'role': 'ppe', 'balance_type': 'credit',
     'name': 'Less: Buildings Accumulated Depreciation', 'parent': 1600},
    {'code': 1620, 'role': 'ppe', 'balance_type': 'debit', 'name': 'Plant', 'parent': 1600},
    {'code': 1621, 'role': 'ppe', 'balance_type': 'credit',
     'name': 'Less: Plant Accumulated Depreciation', 'parent': 1600},
    {'code': 1630, 'role': 'ppe', 'balance_type': 'debit', 'name': 'Equipment', 'parent': 1600},
    {'code': 1631, 'role': 'ppe', 'balance_type': 'credit',
     'name': 'Less: Equipment Accumulated Depreciation', 'parent': 1600},
    {'code': 1640, 'role': 'ppe', 'balance_type': 'debit', 'name': 'Vehicles', 'parent': 1600},
    {'code': 1641, 'role': 'ppe', 'balance_type': 'credit',
     'name': 'Less: Vehicles Accumulated Depreciation', 'parent': 1600},
    {'code': 1650, 'role': 'ppe', 'balance_type': 'debit', 'name': 'Furniture & Fixtures',
     'parent': 1600},
    {'code': 1651, 'role': 'ppe', 'balance_type': 'credit',
     'name': 'Less: Furniture & Fixtures Accumulated Depreciation', 'parent': 1600},

    # INTANGIBLE ASSETS ------
    {'code': 1800, 'role': 'ia', 'balance_type': 'debit', 'name': 'INTANGIBLE ASSETS',
     'parent': 1800},
    {'code': 1810, 'role': 'ia', 'balance_type': 'debit', 'name': 'Goodwill', 'parent': 1800},

    # ADJUSTMENTS ------
    {'code': 1900, 'role': 'aadj', 'balance_type': 'debit', 'name': 'ADJUSTMENTS', 'parent': 1900},
    {'code': 1910, 'role': 'aadj', 'balance_type': 'debit', 'name': 'Securities Unrealized Gains/Losses',
     'parent': 1900},
    {'code': 1920, 'role': 'aadj', 'balance_type': 'debit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': 1900},

    # ---------# ASSETS END #---------#

    # ---------# LIABILITIES START #---------#
    # CURRENT LIABILITIES ------
    {'code': 2000, 'role': 'cl', 'balance_type': 'credit', 'name': 'CURRENT LIABILITIES',
     'parent': 2000},
    {'code': 2010, 'role': 'cl', 'balance_type': 'credit', 'name': 'Current Liabilities',
     'parent': 2000},
    {'code': 2020, 'role': 'cl', 'balance_type': 'credit', 'name': 'Wages Payable', 'parent': 2000},
    {'code': 2030, 'role': 'cl', 'balance_type': 'credit', 'name': 'Interest Payable',
     'parent': 2000},
    {'code': 2040, 'role': 'cl', 'balance_type': 'credit', 'name': 'Short-Term Payable',
     'parent': 2000},
    {'code': 2050, 'role': 'cl', 'balance_type': 'credit', 'name': 'Current Maturities LT Debt',
     'parent': 2000},
    {'code': 2060, 'role': 'cl', 'balance_type': 'credit', 'name': 'Deferred Revenues',
     'parent': 2000},
    {'code': 2070, 'role': 'cl', 'balance_type': 'credit', 'name': 'Other Payables', 'parent': 2000},

    # LIABILITIES ACCOUNTS ------
    {'code': 2100, 'role': 'ltl', 'balance_type': 'credit', 'name': 'LONG TERM LIABILITIES',
     'parent': 2100},
    {'code': 2110, 'role': 'ltl', 'balance_type': 'credit', 'name': 'Long Term Notes Payable',
     'parent': 2100},
    {'code': 2120, 'role': 'ltl', 'balance_type': 'credit', 'name': 'Bonds Payable', 'parent': 2100},
    {'code': 2130, 'role': 'ltl', 'balance_type': 'credit', 'name': 'Mortgage Payable',
     'parent': 2100},

    # ---------# LIABILITIES END #---------#

    # ---------# SHEREHOLDERS EQUITY START #---------#
    # CAPITAL ACCOUNTS ------
    {'code': 3000, 'role': 'cap', 'balance_type': 'credit', 'name': 'CAPITAL ACCOUNTS',
     'parent': 3000},
    {'code': 3010, 'role': 'cap', 'balance_type': 'credit', 'name': 'Capital Account 1',
     'parent': 3000},
    {'code': 3020, 'role': 'cap', 'balance_type': 'credit', 'name': 'Capital Account 2',
     'parent': 3000},
    {'code': 3030, 'role': 'cap', 'balance_type': 'credit', 'name': 'Capital Account 3',
     'parent': 3000},

    # CAPITAL ADJUSTMENTS
    {'code': 3910, 'role': 'cadj', 'balance_type': 'credit',
     'name': 'Available for Sale',
     'parent': 3000},
    {'code': 3920, 'role': 'cadj', 'balance_type': 'credit', 'name': 'PPE Unrealized Gains/Losses',
     'parent': 3000},

    # REVENUE ACCOUNTS ------
    {'code': 4000, 'role': 'in', 'balance_type': 'credit', 'name': 'REVENUE ACCOUNTS',
     'parent': 4000},
    {'code': 4010, 'role': 'in', 'balance_type': 'credit', 'name': 'Sales Income', 'parent': 4000},
    {'code': 4020, 'role': 'in', 'balance_type': 'credit', 'name': 'Rental Income', 'parent': 4000},
    {'code': 4030, 'role': 'in', 'balance_type': 'credit', 'name': 'Property Sales Income',
     'parent': 4000},

    # COGS ACCOUNTS ------
    {'code': 5000, 'role': 'ex', 'balance_type': 'debit', 'name': 'COGS ACCOUNTS', 'parent': 5000},
    {'code': 5010, 'role': 'ex', 'balance_type': 'debit', 'name': 'Cost of Goods Sold',
     'parent': 5000},

    # EXPENSE ACCOUNTS ------
    {'code': 6000, 'role': 'ex', 'balance_type': 'debit', 'name': 'EXPENSE ACCOUNTS', 'parent': 6000},
    {'code': 6010, 'role': 'ex', 'balance_type': 'debit', 'name': 'Advertising', 'parent': 6000},
    {'code': 6020, 'role': 'ex', 'balance_type': 'debit', 'name': 'Amortization', 'parent': 6000},
    {'code': 6030, 'role': 'ex', 'balance_type': 'debit', 'name': 'Auto Expense', 'parent': 6000},
    {'code': 6040, 'role': 'ex', 'balance_type': 'debit', 'name': 'Bad Debt', 'parent': 6000},
    {'code': 6050, 'role': 'ex', 'balance_type': 'debit', 'name': 'Bank Charges', 'parent': 6000},
    {'code': 6060, 'role': 'ex', 'balance_type': 'debit', 'name': 'Commission Expense',
     'parent': 6000},
    {'code': 6070, 'role': 'ex', 'balance_type': 'debit', 'name': 'Depreciation Expense',
     'parent': 6000},
    {'code': 6080, 'role': 'ex', 'balance_type': 'debit', 'name': 'Employee Benefits',
     'parent': 6000},
    {'code': 6090, 'role': 'ex', 'balance_type': 'debit', 'name': 'Freight', 'parent': 6000},
    {'code': 6110, 'role': 'ex', 'balance_type': 'debit', 'name': 'Gifts', 'parent': 6000},
    {'code': 6120, 'role': 'ex', 'balance_type': 'debit', 'name': 'Insurance', 'parent': 6000},
    {'code': 6130, 'role': 'ex', 'balance_type': 'debit', 'name': 'Interest Expense', 'parent': 6000},
    {'code': 6140, 'role': 'ex', 'balance_type': 'debit', 'name': 'Professional Fees',
     'parent': 6000},
    {'code': 6150, 'role': 'ex', 'balance_type': 'debit', 'name': 'License Expense', 'parent': 6000},
    {'code': 6170, 'role': 'ex', 'balance_type': 'debit', 'name': 'Maintenance Expense',
     'parent': 6000},
    {'code': 6180, 'role': 'ex', 'balance_type': 'debit', 'name': 'Meals & Entertainment',
     'parent': 6000},
    {'code': 6190, 'role': 'ex', 'balance_type': 'debit', 'name': 'Office Expense', 'parent': 6000},
    {'code': 6210, 'role': 'ex', 'balance_type': 'debit', 'name': 'Payroll Taxes', 'parent': 6000},
    {'code': 6220, 'role': 'ex', 'balance_type': 'debit', 'name': 'Printing', 'parent': 6000},
    {'code': 6230, 'role': 'ex', 'balance_type': 'debit', 'name': 'Postage', 'parent': 6000},
    {'code': 6240, 'role': 'ex', 'balance_type': 'debit', 'name': 'Rent', 'parent': 6000},

    {'code': 6250, 'role': 'ex', 'balance_type': 'debit', 'name': 'Maintenance & Repairs',
     'parent': 6000},
    {'code': 6251, 'role': 'ex', 'balance_type': 'debit', 'name': 'Maintenance', 'parent': 6000},
    {'code': 6252, 'role': 'ex', 'balance_type': 'debit', 'name': 'Repairs', 'parent': 6000},
    {'code': 6253, 'role': 'ex', 'balance_type': 'debit', 'name': 'HOA', 'parent': 6000},
    {'code': 6254, 'role': 'ex', 'balance_type': 'debit', 'name': 'Snow Removal', 'parent': 6000},
    {'code': 6255, 'role': 'ex', 'balance_type': 'debit', 'name': 'Lawn Care', 'parent': 6000},

    {'code': 6260, 'role': 'ex', 'balance_type': 'debit', 'name': 'Salaries', 'parent': 6000},
    {'code': 6270, 'role': 'ex', 'balance_type': 'debit', 'name': 'Supplies', 'parent': 6000},
    {'code': 6280, 'role': 'ex', 'balance_type': 'debit', 'name': 'Taxes', 'parent': 6000},

    {'code': 6290, 'role': 'ex', 'balance_type': 'debit', 'name': 'Utilities', 'parent': 6000},
    {'code': 6292, 'role': 'ex', 'balance_type': 'debit', 'name': 'Sewer', 'parent': 6000},
    {'code': 6293, 'role': 'ex', 'balance_type': 'debit', 'name': 'Gas', 'parent': 6000},
    {'code': 6294, 'role': 'ex', 'balance_type': 'debit', 'name': 'Garbage', 'parent': 6000},
    {'code': 6295, 'role': 'ex', 'balance_type': 'debit', 'name': 'Electricity', 'parent': 6000},

    {'code': 6300, 'role': 'ex', 'balance_type': 'debit', 'name': 'Property Management',
     'parent': 6000},
    {'code': 6400, 'role': 'ex', 'balance_type': 'debit', 'name': 'Vacancy', 'parent': 6000},

    # MISC REVENUE ACCOUNTS ------
    {'code': 7000, 'role': 'in', 'balance_type': 'credit', 'name': 'MISC. REVENUE ACCOUNTS',
     'parent': 7000},
    {'code': 7010, 'role': 'in', 'balance_type': 'credit', 'name': 'Misc. Revenue', 'parent': 7000},

    # MISC EXPENSE ACCOUNTS ------
    {'code': 7500, 'role': 'ex', 'balance_type': 'debit', 'name': 'MISC. EXPENSE ACCOUNTS',
     'parent': 7500},
    {'code': 7510, 'role': 'ex', 'balance_type': 'debit', 'name': 'Misc. Expense', 'parent': 7500},

    # ---------# SHAREHOLDER'S EQUITY END #---------#

]
