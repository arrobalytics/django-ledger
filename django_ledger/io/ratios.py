"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

RATIO_NA = 0


class FinancialRatioManager:

    def __init__(self, io_data):
        self.DIGEST = io_data
        self.ACCOUNTS = io_data['accounts']
        self.RATIO_NA = RATIO_NA

        self.quick_assets = io_data['group_balance']['GROUP_QUICK_ASSETS']
        self.assets = io_data['group_balance']['GROUP_ASSETS']
        self.current_liabilities = io_data['group_balance']['GROUP_CURRENT_LIABILITIES']
        self.current_assets = io_data['group_balance']['GROUP_CURRENT_ASSETS']
        self.equity = io_data['group_balance']['GROUP_CAPITAL']
        self.liabilities = io_data['group_balance']['GROUP_LIABILITIES']
        self.net_income = io_data['group_balance']['GROUP_EARNINGS']
        self.net_sales = io_data['group_balance']['GROUP_NET_SALES']
        self.net_profit = io_data['group_balance']['GROUP_NET_PROFIT']
        self.gross_profit = io_data['group_balance']['GROUP_GROSS_PROFIT']
        self.RATIOS = dict()

    def digest(self):
        self.quick_ratio()
        self.current_ratio()
        self.debt_to_equity()
        self.return_on_equity()
        self.return_on_assets()
        self.net_profit_margin()
        self.gross_profit_margin()
        self.DIGEST['ratios'] = self.RATIOS
        return self.DIGEST

    # ------> SOLVENCY RATIOS <------
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

    # ------> LEVERAGE RATIOS <------
    def debt_to_equity(self, as_percent=False):
        if self.equity == 0:
            cr = RATIO_NA
        else:
            cr = self.liabilities / self.equity
            if as_percent:
                cr = cr * 100
        self.RATIOS['debt_to_equity'] = cr

    # ------> PROFITABILITY RATIOS <------
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
