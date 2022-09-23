from django.core.exceptions import ValidationError

from django_ledger.io.io_context import GroupManager


class CashFlowStatementError(ValidationError):
    pass


class CashFlowStatement:
    CFS_DIGEST_KEY = 'cash_flow_statement'

    def __init__(self,
                 io_digest: dict,
                 by_period: bool = False,
                 by_unit: bool = False):
        self.IO_DIGEST = io_digest

    def check_io_digest(self):
        if GroupManager.GROUP_BALANCE_KEY not in self.IO_DIGEST:
            raise CashFlowStatementError(
                'IO Digest must have groups for Cash Flow Statement'
            )

    def digest(self):
        self.check_io_digest()
        operating_activities = list()
        operating_activities.append({
            'description': 'Net Income',
            'balance': self.IO_DIGEST[GroupManager.GROUP_BALANCE_KEY]['GROUP_CFS_NET_INCOME']
        })
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['operating'] = operating_activities

        return self.IO_DIGEST
