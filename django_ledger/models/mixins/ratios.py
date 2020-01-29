from django_ledger.models_abstracts import account_roles as roles

"""
	1.	Current ratio
	2.	Quick ratio
	3.	Absolute liquidity ratio
	4.	Cash ratio
	5.	Inventory Turnover Ratio
	6.	Receivables Turnover Ratio
	7.	Capital Turnover Ratio
	8.	Asset Turnover Ratio
	9.	Net Working Capital Ratio
	10.	Cash Conversion Cycle
	11.	Earnings Margin
	12.	Return on Investment
	13.	Return on Equity
	14.	Earnings Per Share
	15.	Operating Leverage
	16.	Financial leverage
	17.	Total Leverage
	18.	Debt-Equity Ratio
	19.	Interest Coverage Ratio
	20.	Debt Service Coverage Ratio
	21.	Fixed Asset Ratio
	22.	Current Asset to Fixed Asset
	23.	Proprietary Ratio
	24.	Fixed Interest Cover
	25.	Fixed Dividend Cover
	26.	Capacity Ratio
	27.	Activity Ratio
	28.	Efficiency Ratio
"""


def bs_current_ratio(tx_data, digest):
    current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_LIABILITIES])
    current_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_ASSETS])
    if current_liabilities == 0:
        current_ratio = '-inf-'
    else:
        current_ratio = current_assets / current_liabilities
    digest['ratios']['bs_current_ratio'] = current_ratio


def bs_quick_ratio(tx_data, digest):
    current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_LIABILITIES])
    quick_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_QUICK_ASSETS])
    if current_liabilities == 0:
        quick_ratio = '-inf-'
    else:
        quick_ratio = quick_assets / current_liabilities
    digest['ratios']['bs_quick_ratio'] = quick_ratio


def bs_cash_ratio(data):
    pass


def generate_ratios(digest: dict, data: list) -> dict:
    bs_current_ratio(data, digest)
    bs_quick_ratio(data, digest)
    return digest
