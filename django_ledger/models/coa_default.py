CHART_OF_ACCOUNTS = [

    # ---------# ASSETS START #---------#
    # CURRENT ASSET  ------
    {'acc_code': 1000, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'CURRENT ASSETS', 'acc_parent': 1000},
    {'acc_code': 1010, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Cash', 'acc_parent': 1000},
    {'acc_code': 1050, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Short Term Investments',
     'acc_parent': 1000},
    {'acc_code': 1100, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Accounts Receivable',
     'acc_parent': 1000},
    {'acc_code': 1101, 'acc_role': 'ca', 'acc_type': 'credit', 'acc_name': 'Uncollectibles', 'acc_parent': 1100},
    {'acc_code': 1200, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Inventory', 'acc_parent': 1000},
    {'acc_code': 1300, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Prepaid Expenses', 'acc_parent': 1000},

    # LONG TERM IMVESTMENTS ------
    {'acc_code': 1500, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'LONG TERM INVESTMENTS',
     'acc_parent': 1500},
    {'acc_code': 1510, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Notes Receivable', 'acc_parent': 1500},
    {'acc_code': 1520, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Land', 'acc_parent': 1500},
    {'acc_code': 1530, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Securities', 'acc_parent': 1500},

    # PPE ------
    {'acc_code': 1600, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'PPE', 'acc_parent': 1600},
    {'acc_code': 1610, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Buildings', 'acc_parent': 1600},
    {'acc_code': 1611, 'acc_role': 'ppe', 'acc_type': 'credit',
     'acc_name': 'Less: Buildings Accumulated Depreciation', 'acc_parent': 1600},
    {'acc_code': 1620, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Plant', 'acc_parent': 1600},
    {'acc_code': 1621, 'acc_role': 'ppe', 'acc_type': 'credit',
     'acc_name': 'Less: Plant Accumulated Depreciation', 'acc_parent': 1600},
    {'acc_code': 1630, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Equipment', 'acc_parent': 1600},
    {'acc_code': 1631, 'acc_role': 'ppe', 'acc_type': 'credit',
     'acc_name': 'Less: Equipment Accumulated Depreciation', 'acc_parent': 1600},
    {'acc_code': 1640, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Vehicles', 'acc_parent': 1600},
    {'acc_code': 1641, 'acc_role': 'ppe', 'acc_type': 'credit',
     'acc_name': 'Less: Vehicles Accumulated Depreciation', 'acc_parent': 1600},
    {'acc_code': 1650, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Furniture & Fixtures',
     'acc_parent': 1600},
    {'acc_code': 1651, 'acc_role': 'ppe', 'acc_type': 'credit',
     'acc_name': 'Less: Furniture & Fixtures Accumulated Depreciation', 'acc_parent': 1600},

    # INTANGIBLE ASSETS ------
    {'acc_code': 1800, 'acc_role': 'ia', 'acc_type': 'debit', 'acc_name': 'INTANGIBLE ASSETS',
     'acc_parent': 1800},
    {'acc_code': 1810, 'acc_role': 'ia', 'acc_type': 'debit', 'acc_name': 'Goodwill', 'acc_parent': 1800},

    # ADJUSTMENTS ------
    {'acc_code': 1900, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'ADJUSTMENTS', 'acc_parent': 1900},
    {'acc_code': 1910, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'Securities Unrealized Gains/Losses',
     'acc_parent': 1900},
    {'acc_code': 1920, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'PPE Unrealized Gains/Losses',
     'acc_parent': 1900},

    # ---------# ASSETS END #---------#

    # ---------# LIABILITIES START #---------#
    # CURRENT LIABILITIES ------
    {'acc_code': 2000, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'CURRENT LIABILITIES',
     'acc_parent': 2000},
    {'acc_code': 2010, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Current Liabilities',
     'acc_parent': 2000},
    {'acc_code': 2020, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Wages Payable', 'acc_parent': 2000},
    {'acc_code': 2030, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Interest Payable',
     'acc_parent': 2000},
    {'acc_code': 2040, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Short-Term Payable',
     'acc_parent': 2000},
    {'acc_code': 2050, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Current Maturities LT Debt',
     'acc_parent': 2000},
    {'acc_code': 2060, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Deferred Revenues',
     'acc_parent': 2000},
    {'acc_code': 2070, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Other Payables', 'acc_parent': 2000},

    # LIABILITIES ACCOUNTS ------
    {'acc_code': 2100, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'LONG TERM LIABILITIES',
     'acc_parent': 2100},
    {'acc_code': 2110, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Long Term Notes Payable',
     'acc_parent': 2100},
    {'acc_code': 2120, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Bonds Payable', 'acc_parent': 2100},
    {'acc_code': 2130, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Mortgage Payable',
     'acc_parent': 2100},

    # ---------# LIABILITIES END #---------#

    # ---------# SHEREHOLDERS EQUITY START #---------#
    # CAPITAL ACCOUNTS ------
    {'acc_code': 3000, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'CAPITAL ACCOUNTS',
     'acc_parent': 3000},
    {'acc_code': 3010, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 1',
     'acc_parent': 3000},
    {'acc_code': 3020, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 2',
     'acc_parent': 3000},
    {'acc_code': 3030, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 3',
     'acc_parent': 3000},

    # CAPITAL ADJUSTMENTS
    {'acc_code': 3910, 'acc_role': 'cadj', 'acc_type': 'credit',
     'acc_name': 'Available for Sale',
     'acc_parent': 3000},
    {'acc_code': 3920, 'acc_role': 'cadj', 'acc_type': 'credit', 'acc_name': 'PPE Unrealized Gains/Losses',
     'acc_parent': 3000},

    # REVENUE ACCOUNTS ------
    {'acc_code': 4000, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'REVENUE ACCOUNTS',
     'acc_parent': 4000},
    {'acc_code': 4010, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Sales Income', 'acc_parent': 4000},
    {'acc_code': 4020, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Rental Income', 'acc_parent': 4000},
    {'acc_code': 4030, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Property Sales Income',
     'acc_parent': 4000},

    # COGS ACCOUNTS ------
    {'acc_code': 5000, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'COGS ACCOUNTS', 'acc_parent': 5000},
    {'acc_code': 5010, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Cost of Goods Sold',
     'acc_parent': 5000},

    # EXPENSE ACCOUNTS ------
    {'acc_code': 6000, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'EXPENSE ACCOUNTS', 'acc_parent': 6000},
    {'acc_code': 6010, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Advertising', 'acc_parent': 6000},
    {'acc_code': 6020, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Amortization', 'acc_parent': 6000},
    {'acc_code': 6030, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Auto Expense', 'acc_parent': 6000},
    {'acc_code': 6040, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Bad Debt', 'acc_parent': 6000},
    {'acc_code': 6050, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Bank Charges', 'acc_parent': 6000},
    {'acc_code': 6060, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Commission Expense',
     'acc_parent': 6000},
    {'acc_code': 6070, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Depreciation Expense',
     'acc_parent': 6000},
    {'acc_code': 6080, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Employee Benefits',
     'acc_parent': 6000},
    {'acc_code': 6090, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Freight', 'acc_parent': 6000},
    {'acc_code': 6110, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Gifts', 'acc_parent': 6000},
    {'acc_code': 6120, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Insurance', 'acc_parent': 6000},
    {'acc_code': 6130, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Interest Expense', 'acc_parent': 6000},
    {'acc_code': 6140, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Professional Fees',
     'acc_parent': 6000},
    {'acc_code': 6150, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'License Expense', 'acc_parent': 6000},
    {'acc_code': 6170, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance Expense',
     'acc_parent': 6000},
    {'acc_code': 6180, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Meals & Entertainment',
     'acc_parent': 6000},
    {'acc_code': 6190, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Office Expense', 'acc_parent': 6000},
    {'acc_code': 6210, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Payroll Taxes', 'acc_parent': 6000},
    {'acc_code': 6220, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Printing', 'acc_parent': 6000},
    {'acc_code': 6230, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Postage', 'acc_parent': 6000},
    {'acc_code': 6240, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Rent', 'acc_parent': 6000},

    {'acc_code': 6250, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance & Repairs',
     'acc_parent': 6000},
    {'acc_code': 6251, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance', 'acc_parent': 6000},
    {'acc_code': 6252, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Repairs', 'acc_parent': 6000},
    {'acc_code': 6253, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'HOA', 'acc_parent': 6000},
    {'acc_code': 6254, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Snow Removal', 'acc_parent': 6000},
    {'acc_code': 6255, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Lawn Care', 'acc_parent': 6000},

    {'acc_code': 6260, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Salaries', 'acc_parent': 6000},
    {'acc_code': 6270, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Supplies', 'acc_parent': 6000},
    {'acc_code': 6280, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Taxes', 'acc_parent': 6000},

    {'acc_code': 6290, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Utilities', 'acc_parent': 6000},
    {'acc_code': 6292, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Sewer', 'acc_parent': 6000},
    {'acc_code': 6293, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Gas', 'acc_parent': 6000},
    {'acc_code': 6294, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Garbage', 'acc_parent': 6000},
    {'acc_code': 6295, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Electricity', 'acc_parent': 6000},

    {'acc_code': 6300, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Property Management',
     'acc_parent': 6000},
    {'acc_code': 6400, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Vacancy', 'acc_parent': 6000},

    # MISC REVENUE ACCOUNTS ------
    {'acc_code': 7000, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'MISC. REVENUE ACCOUNTS',
     'acc_parent': 7000},
    {'acc_code': 7010, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Misc. Revenue', 'acc_parent': 7000},

    # MISC EXPENSE ACCOUNTS ------
    {'acc_code': 7500, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'MISC. EXPENSE ACCOUNTS',
     'acc_parent': 7500},
    {'acc_code': 7510, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Misc. Expense', 'acc_parent': 7500},

    # ---------# SHAREHOLDER'S EQUITY END #---------#

]
