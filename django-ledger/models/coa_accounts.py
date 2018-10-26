CHART_OF_ACCOUNTS = {

    # ---------# ASSETS START #---------#
    # CURRENT ASSET  ------
    '1': {'acc_code': 1000, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'CURRENT ASSETS', 'acc_parent': 1000},
    '2': {'acc_code': 1010, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Cash', 'acc_parent': 1000},
    '3': {'acc_code': 1050, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Short Term Investments',
          'acc_parent': 1000},
    '4': {'acc_code': 1100, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Accounts Receivable',
          'acc_parent': 1000},
    '5': {'acc_code': 1101, 'acc_role': 'ca', 'acc_type': 'credit', 'acc_name': 'Uncollectibles', 'acc_parent': 1100},
    '6': {'acc_code': 1200, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Inventory', 'acc_parent': 1000},
    '7': {'acc_code': 1300, 'acc_role': 'ca', 'acc_type': 'debit', 'acc_name': 'Prepaid Expenses', 'acc_parent': 1000},

    # LONG TERM IMVESTMENTS ------
    '8': {'acc_code': 1500, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'LONG TERM INVESTMENTS',
          'acc_parent': 1500},
    '9': {'acc_code': 1510, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Notes Receivable', 'acc_parent': 1500},
    '10': {'acc_code': 1520, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Land', 'acc_parent': 1500},
    '11': {'acc_code': 1530, 'acc_role': 'lti', 'acc_type': 'debit', 'acc_name': 'Securities', 'acc_parent': 1500},

    # PPE ------
    '12': {'acc_code': 1600, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'PPE', 'acc_parent': 1600},
    '13': {'acc_code': 1610, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Buildings', 'acc_parent': 1600},
    '14': {'acc_code': 1611, 'acc_role': 'ppe', 'acc_type': 'credit',
           'acc_name': 'Less: Buildings Accumulated Depreciation', 'acc_parent': 1600},
    '15': {'acc_code': 1620, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Plant', 'acc_parent': 1600},
    '16': {'acc_code': 1621, 'acc_role': 'ppe', 'acc_type': 'credit',
           'acc_name': 'Less: Plant Accumulated Depreciation', 'acc_parent': 1600},
    '17': {'acc_code': 1630, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Equipment', 'acc_parent': 1600},
    '18': {'acc_code': 1631, 'acc_role': 'ppe', 'acc_type': 'credit',
           'acc_name': 'Less: Equipment Accumulated Depreciation', 'acc_parent': 1600},
    '101': {'acc_code': 1640, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Vehicles', 'acc_parent': 1600},
    '102': {'acc_code': 1640, 'acc_role': 'ppe', 'acc_type': 'credit',
            'acc_name': 'Less: Vehicles Accumulated Depreciation', 'acc_parent': 1600},
    '103': {'acc_code': 1650, 'acc_role': 'ppe', 'acc_type': 'debit', 'acc_name': 'Furniture & Fixtures',
            'acc_parent': 1600},
    '104': {'acc_code': 1651, 'acc_role': 'ppe', 'acc_type': 'credit',
            'acc_name': 'Less: Furniture & Fixtures Accumulated Depreciation', 'acc_parent': 1600},

    # INTANGIBLE ASSETS ------
    '110': {'acc_code': 1800, 'acc_role': 'ia', 'acc_type': 'debit', 'acc_name': 'INTANGIBLE ASSETS',
            'acc_parent': 1800},
    '111': {'acc_code': 1810, 'acc_role': 'ia', 'acc_type': 'debit', 'acc_name': 'Goodwill', 'acc_parent': 1800},

    # ADJUSTMENTS ------
    '19': {'acc_code': 1900, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'ADJUSTMENTS', 'acc_parent': 1900},
    '20': {'acc_code': 1910, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'Securities Unrealized Gains/Losses',
           'acc_parent': 1900},
    '21': {'acc_code': 1920, 'acc_role': 'aadj', 'acc_type': 'debit', 'acc_name': 'PPE Unrealized Gains/Losses',
           'acc_parent': 1900},

    # ---------# ASSETS END #---------#

    # ---------# LIABILITIES START #---------#
    # CURRENT LIABILITIES ------
    '23': {'acc_code': 2000, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'CURRENT LIABILITIES',
           'acc_parent': 2000},
    '24': {'acc_code': 2010, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Current Liabilities',
           'acc_parent': 2000},
    '25': {'acc_code': 2020, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Wages Payable', 'acc_parent': 2000},
    '26': {'acc_code': 2030, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Interest Payable',
           'acc_parent': 2000},
    '27': {'acc_code': 2040, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Short-Term Payable',
           'acc_parent': 2000},
    '28': {'acc_code': 2050, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Current Maturities LT Debt',
           'acc_parent': 2000},
    '29': {'acc_code': 2060, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Deferred Revenues',
           'acc_parent': 2000},
    '30': {'acc_code': 2070, 'acc_role': 'cl', 'acc_type': 'credit', 'acc_name': 'Other Payables', 'acc_parent': 2000},

    # LIABILITIES ACCOUNTS ------
    '31': {'acc_code': 2100, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'LONG TERM LIABILITIES',
           'acc_parent': 2100},
    '32': {'acc_code': 2110, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Long Term Notes Payable',
           'acc_parent': 2100},
    '33': {'acc_code': 2120, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Bonds Payable', 'acc_parent': 2100},
    '34': {'acc_code': 2130, 'acc_role': 'ltl', 'acc_type': 'credit', 'acc_name': 'Mortgage Payable',
           'acc_parent': 2100},

    # ---------# LIABILITIES END #---------#

    # ---------# SHEREHOLDERS EQUITY START #---------#
    # CAPITAL ACCOUNTS ------
    '35': {'acc_code': 3000, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'CAPITAL ACCOUNTS',
           'acc_parent': 3000},
    '36': {'acc_code': 3010, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 1',
           'acc_parent': 3000},
    '37': {'acc_code': 3020, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 2',
           'acc_parent': 3000},
    '38': {'acc_code': 3030, 'acc_role': 'cap', 'acc_type': 'credit', 'acc_name': 'Capital Account 3',
           'acc_parent': 3000},

    # CAPITAL ADJUSTMENTS
    '107': {'acc_code': 3910, 'acc_role': 'cadj', 'acc_type': 'credit',
            'acc_name': 'Available for Sale',
            'acc_parent': 3000},
    '106': {'acc_code': 3920, 'acc_role': 'cadj', 'acc_type': 'credit', 'acc_name': 'PPE Unrealized Gains/Losses',
            'acc_parent': 3000},

    # REVENUE ACCOUNTS ------
    '39': {'acc_code': 4000, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'REVENUE ACCOUNTS',
           'acc_parent': 4000},
    '40': {'acc_code': 4010, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Sales Income', 'acc_parent': 4000},
    '41': {'acc_code': 4020, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Rental Income', 'acc_parent': 4000},
    '105': {'acc_code': 4030, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Property Sales Income',
            'acc_parent': 4000},

    # COGS ACCOUNTS ------
    '42': {'acc_code': 5000, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'COGS ACCOUNTS', 'acc_parent': 5000},
    '43': {'acc_code': 5010, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Cost of Goods Sold',
           'acc_parent': 5000},

    # EXPENSE ACCOUNTS ------
    '44': {'acc_code': 6000, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'EXPENSE ACCOUNTS', 'acc_parent': 6000},
    '45': {'acc_code': 6010, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Advertising', 'acc_parent': 6000},
    '46': {'acc_code': 6020, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Amortization', 'acc_parent': 6000},
    '47': {'acc_code': 6030, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Auto Expense', 'acc_parent': 6000},
    '48': {'acc_code': 6040, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Bad Debt', 'acc_parent': 6000},
    '49': {'acc_code': 6050, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Bank Charges', 'acc_parent': 6000},
    '50': {'acc_code': 6060, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Commission Expense',
           'acc_parent': 6000},
    '51': {'acc_code': 6070, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Depreciation Expense',
           'acc_parent': 6000},
    '52': {'acc_code': 6080, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Employee Benefits',
           'acc_parent': 6000},
    '53': {'acc_code': 6090, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Freight', 'acc_parent': 6000},
    '54': {'acc_code': 6110, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Gifts', 'acc_parent': 6000},
    '55': {'acc_code': 6120, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Insurance', 'acc_parent': 6000},
    '56': {'acc_code': 6130, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Interest Expense', 'acc_parent': 6000},
    '57': {'acc_code': 6140, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Professional Fees',
           'acc_parent': 6000},
    '58': {'acc_code': 6150, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'License Expense', 'acc_parent': 6000},
    '59': {'acc_code': 6170, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance Expense',
           'acc_parent': 6000},
    '60': {'acc_code': 6180, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Meals & Entertainment',
           'acc_parent': 6000},
    '61': {'acc_code': 6190, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Office Expense', 'acc_parent': 6000},
    '62': {'acc_code': 6210, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Payroll Taxes', 'acc_parent': 6000},
    '63': {'acc_code': 6220, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Printing', 'acc_parent': 6000},
    '64': {'acc_code': 6230, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Postage', 'acc_parent': 6000},
    '65': {'acc_code': 6240, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Rent', 'acc_parent': 6000},

    '66': {'acc_code': 6250, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance & Repairs',
           'acc_parent': 6000},
    '67': {'acc_code': 6251, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Maintenance', 'acc_parent': 6000},
    '68': {'acc_code': 6252, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Repairs', 'acc_parent': 6000},
    '69': {'acc_code': 6253, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'HOA', 'acc_parent': 6000},
    '70': {'acc_code': 6254, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Snow Removal', 'acc_parent': 6000},
    '71': {'acc_code': 6255, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Lawn Care', 'acc_parent': 6000},

    '72': {'acc_code': 6260, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Salaries', 'acc_parent': 6000},
    '73': {'acc_code': 6270, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Supplies', 'acc_parent': 6000},
    '74': {'acc_code': 6280, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Taxes', 'acc_parent': 6000},

    '75': {'acc_code': 6290, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Utilities', 'acc_parent': 6000},
    '77': {'acc_code': 6292, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Sewer', 'acc_parent': 6000},
    '78': {'acc_code': 6293, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Gas', 'acc_parent': 6000},
    '79': {'acc_code': 6294, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Garbage', 'acc_parent': 6000},
    '80': {'acc_code': 6295, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Electricity', 'acc_parent': 6000},

    '81': {'acc_code': 6300, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Property Management',
           'acc_parent': 6000},
    '82': {'acc_code': 6400, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Vacancy', 'acc_parent': 6000},

    ### CAP EXPENDITURES ###
    # '83': {'acc_code': 6900, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'CAPITAL EXPENDITURES',
    #        'acc_parent': 6900},
    '84': {'acc_code': 6901, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Roof', 'acc_parent': 6000},
    '85': {'acc_code': 6902, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Water Heater', 'acc_parent': 6000},
    '86': {'acc_code': 6903, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Appliances', 'acc_parent': 6000},
    '87': {'acc_code': 6904, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Driveway & Parking',
           'acc_parent': 6000},
    '88': {'acc_code': 6905, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'HVAC', 'acc_parent': 6000},
    '89': {'acc_code': 6906, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Floring', 'acc_parent': 6000},
    '90': {'acc_code': 6907, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Plumbing', 'acc_parent': 6000},
    '91': {'acc_code': 6908, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Windows', 'acc_parent': 6000},
    '92': {'acc_code': 6909, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Paint', 'acc_parent': 6000},
    '93': {'acc_code': 6910, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Cabinets & Counters',
           'acc_parent': 6000},
    '94': {'acc_code': 6911, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Structure', 'acc_parent': 6000},
    '95': {'acc_code': 6912, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Components', 'acc_parent': 6000},
    '96': {'acc_code': 6913, 'acc_role': 'capex', 'acc_type': 'debit', 'acc_name': 'Landscaping', 'acc_parent': 6000},

    # MISC REVENUE ACCOUNTS ------
    '97': {'acc_code': 7000, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'MISC. REVENUE ACCOUNTS',
           'acc_parent': 7000},
    '98': {'acc_code': 7010, 'acc_role': 'in', 'acc_type': 'credit', 'acc_name': 'Misc. Revenue', 'acc_parent': 7000},

    # MISC EXPENSE ACCOUNTS ------
    '99': {'acc_code': 7500, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'MISC. EXPENSE ACCOUNTS',
           'acc_parent': 7500},
    '100': {'acc_code': 7510, 'acc_role': 'ex', 'acc_type': 'debit', 'acc_name': 'Misc. Expense', 'acc_parent': 7500},

    # ---------# SHAREHOLDER'S EQUITY END #---------#

}
