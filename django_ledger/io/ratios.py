from django_ledger.io import roles as roles

RATIO_NA = 'NA'


class FinancialRatioGenerator:

    def __init__(self, tx_digest, tx_data):
        self.DIGEST = tx_digest
        self.TX_DATA = tx_data
        self.RATIO_NA = RATIO_NA

        self.quick_assets = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_QUICK_ASSETS])
        self.current_liabilities = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_CURRENT_LIABILITIES])
        self.current_assets = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_CURRENT_ASSETS])
        self.equity = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_EQUITY])
        self.debt = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_LIABILITIES])

        self.net_income = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_EARNINGS])
        self.net_sales = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_NET_SALES])
        self.net_profit = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_NET_PROFIT])
        self.gross_profit = sum([acc['balance'] for acc in self.TX_DATA if acc['role'] in roles.GROUP_GROSS_PROFIT])

        self.assets = sum([acc['balance'] for acc in self.TX_DATA if acc['role_bs'] == 'assets'])
        self.RATIOS = dict()

    def generate(self):
        self.quick_ratio()
        self.current_ratio()
        self.debt_to_equity()
        self.return_on_equity()
        self.return_on_assets()
        self.net_profit_margin()
        self.gross_profit_margin()
        self.DIGEST['ratios'] = self.RATIOS
        # print(self.DIGEST['ratios'])

    def quick_ratio(self, as_percent=False):
        if self.current_liabilities == 0:
            cr = self.RATIO_NA
        else:
            cr = self.quick_assets / self.current_liabilities
            if as_percent:
                cr = cr * 100
        self.RATIOS['quick_ratio'] = cr

    def current_ratio(self, as_percent=False):
        if self.current_liabilities == 0:
            cr = RATIO_NA
        else:
            cr = self.current_assets / self.current_liabilities
            if as_percent:
                cr = cr * 100
        self.RATIOS['current_ratio'] = cr

    def debt_to_equity(self, as_percent=False):
        if self.equity == 0:
            cr = RATIO_NA
        else:
            cr = self.debt / self.equity
            if as_percent:
                cr = cr * 100
        self.RATIOS['debt_to_equity'] = cr

    def return_on_equity(self, as_percent=False):
        if self.equity == 0:
            cr = RATIO_NA
        else:
            cr = self.net_income / self.equity
            if as_percent:
                cr = cr * 100
        self.RATIOS['return_on_equity'] = cr

    def return_on_assets(self, as_percent=False):
        if self.assets == 0:
            cr = RATIO_NA
        else:
            cr = self.net_income / self.assets
            if as_percent:
                cr = cr * 100
        self.RATIOS['return_on_assets'] = cr

    def net_profit_margin(self, as_percent=False):
        if self.net_sales == 0:
            npm = RATIO_NA
        else:
            npm = self.net_profit / self.net_sales
            if as_percent:
                npm = npm * 100
        self.RATIOS['net_profit_margin'] = npm

    def gross_profit_margin(self, as_percent=False):
        if self.gross_profit == 0:
            gpm = RATIO_NA
        else:
            gpm = self.gross_profit / self.net_sales
            if as_percent:
                gpm = gpm * 100
        self.RATIOS['gross_profit_margin'] = gpm


# PROFITABILITY RATIOS

# SOLVENCY RATIOS

# LEVERAGE RATIOS

# def bs_current_ratio(tx_data, digest, as_percent=False):
#     current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_CURRENT_LIABILITIES])
#     if current_liabilities == 0:
#         cr = RATIO_NA
#     else:
#         current_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_CURRENT_ASSETS])
#         cr = current_assets / current_liabilities
#         if as_percent:
#             cr = cr * 100
#     digest['ratios']['bs_current_ratio'] = cr
#
#
# def bs_quick_ratio(tx_data, digest, as_percent=False):
#     current_liabilities = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_CURRENT_LIABILITIES])
#     if current_liabilities == 0:
#         qr = RATIO_NA
#     else:
#         quick_assets = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_QUICK_ASSETS])
#         qr = quick_assets / current_liabilities
#         if as_percent:
#             qr = qr * 100
#     digest['ratios']['bs_quick_ratio'] = qr
#
#
# def bs_debt_to_equity(tx_data, digest, as_percent=False):
#     equity = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_EQUITY])
#     if equity == 0:
#         dte = RATIO_NA
#     else:
#         debt = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_LIABILITIES])
#         dte = debt / equity
#         if as_percent:
#             dte = dte * 100
#     digest['ratios']['bs_debt_to_equity_ratio'] = dte
#

# def bs_roe(tx_data, digest, as_percent=False):
#     """
#     Return on Equity Ratio
#     :param tx_data:
#     :param digest:
#     :param as_percent:
#     """
#     equity = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_EQUITY])
#     if equity == 0:
#         roe = RATIO_NA
#     else:
#         net_income = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_EARNINGS])
#         roe = net_income / equity
#         if as_percent:
#             roe = roe * 100
#     digest['ratios']['bs_roe'] = roe
#
#
# def bs_roa(tx_data, digest, as_percent=False):
#     """
#     Return on Assets
#     :param tx_data:
#     :param digest:
#     :param as_percent:
#     """
#     assets = sum([acc['balance'] for acc in tx_data if acc['role_bs'] == 'assets'])
#     if assets == 0:
#         roa = RATIO_NA
#     else:
#         net_income = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_EARNINGS])
#         roa = net_income / assets
#         if as_percent:
#             roa = roa * 100
#     digest['ratios']['bs_roa'] = roa
#
#
# def is_net_profit_margin(tx_data, digest, as_percent=False):
#     net_sales = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_NET_SALES])
#     if net_sales == 0:
#         npm = RATIO_NA
#     else:
#         net_profit = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_NET_PROFIT])
#         npm = net_profit / net_sales
#         if as_percent:
#             npm = npm * 100
#     digest['ratios']['ic_net_profit_margin'] = npm
#
#
# def is_gross_profit_margin(tx_data, digest, as_percent=False):
#     gross_profit = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_GROSS_PROFIT])
#     if gross_profit == 0:
#         gpm = RATIO_NA
#     else:
#         net_sales = sum([acc['balance'] for acc in tx_data if acc['role'] in roles.GROUP_NET_SALES])
#         gpm = gross_profit / net_sales
#         if as_percent:
#             gpm = gpm * 100
#     digest['ratios']['ic_gross_profit_margin'] = gpm
#
#
# def generate_ratios(tx_data: list, digest: dict) -> dict:
#     bs_current_ratio(tx_data, digest)
#     bs_quick_ratio(tx_data, digest)
#     bs_debt_to_equity(tx_data, digest)
#     bs_roe(tx_data, digest)
#     bs_roa(tx_data, digest)
#
#     is_net_profit_margin(tx_data, digest)
#     is_gross_profit_margin(tx_data, digest)
#
#     return digest
