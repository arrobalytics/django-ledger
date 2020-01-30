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

RATIO_NA = 'NA'


def bs_current_ratio(tx_data, digest):
    current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_LIABILITIES])
    current_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_ASSETS])
    if current_liabilities == 0:
        digest['ratios']['bs_current_ratio'] = RATIO_NA
    else:
        digest['ratios']['bs_current_ratio'] = current_assets / current_liabilities


def bs_quick_ratio(tx_data, digest):
    current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CURRENT_LIABILITIES])
    quick_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_QUICK_ASSETS])
    if current_liabilities == 0:
        digest['ratios']['bs_quick_ratio'] = RATIO_NA
    else:
        digest['ratios']['bs_quick_ratio'] = quick_assets / current_liabilities


def bs_debt_to_equity(tx_data, digest):
    debt = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_LIABILITIES])
    equity = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CAPITAL])
    if equity == 0:
        digest['ratios']['bs_debt_to_equity_ratio'] = RATIO_NA
    else:
        digest['ratios']['bs_debt_to_equity_ratio'] = debt / equity


def bs_roe(tx_data, digest, as_percent=False):
    """
    Return on Equity Ratio
    :param tx_data:
    :param digest:
    :param as_percent:
    """
    net_income = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_EARNINGS])
    equity = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_CAPITAL])
    if equity == 0:
        digest['ratios']['bs_roe'] = RATIO_NA
    else:
        roe = net_income / equity
        if as_percent:
            roe = roe * 100
        digest['ratios']['bs_roe'] = roe


def bs_roa(tx_data, digest, as_percent=False):
    """
    Return on Assets
    :param tx_data:
    :param digest:
    :param as_percent:
    """
    pass


def ic_net_profit_margin(tx_data, digest):
    net_profit = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_NET_PROFIT])
    net_sales = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_NET_SALES])
    if net_sales == 0:
        digest['ratios']['ic_net_profit_margin'] = RATIO_NA
    else:
        digest['ratios']['ic_net_profit_margin'] = net_profit / net_sales


def ic_gross_profit_margin(tx_data, digest):
    gross_profit = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_GROSS_PROFIT])
    net_sales = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.ROLES_NET_SALES])
    if gross_profit == 0:
        digest['ratios']['ic_net_profit_margin'] = RATIO_NA
    else:
        digest['ratios']['ic_net_profit_margin'] = gross_profit / net_sales


def generate_ratios(tx_data: list, digest: dict) -> dict:
    bs_current_ratio(tx_data, digest)
    bs_quick_ratio(tx_data, digest)
    bs_debt_to_equity(tx_data, digest)
    bs_roe(tx_data, digest)

    ic_net_profit_margin(tx_data, digest)
    ic_gross_profit_margin(tx_data, digest)

    return digest
