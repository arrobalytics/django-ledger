"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import chain
from typing import Union, Dict, Callable, Optional
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import get_localtime
from django_ledger.models.accounts import AccountModel, AccountModelQuerySet, CREDIT, DEBIT
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.ledger import LedgerModel, LedgerModelQuerySet


@dataclass
class TransactionInstructionItem:
    """
    A class to represent a transaction instruction used during the development of transaction blueprints.

    Attributes
    ----------
    account_code: str
        The account code of the AccountModel as a String.
    amount: Decimal
        The transaction amount as a Decimal value. Will be rounded to the nearest decimal place.
    tx_type: str
        A choice of 'debit' or 'credit' transaction.
    description: str
        Description of the transaction.
    account_model: AccountModel
        The resolved account model for the transaction. Not to be modified. Defaults to None.
    """
    account_code: str
    amount: Union[Decimal, float]
    tx_type: str
    description: Optional[str]
    account_model: Optional[AccountModel] = None

    def to_dict(self) -> Dict:
        return {
            'account': self.account_model,
            'amount': self.amount,
            'tx_type': self.tx_type,
            'description': self.description
        }


class IOCursorValidationError(ValidationError):
    pass


class IOCursor:

    def __init__(self,
                 io_library,
                 entity_model: EntityModel,
                 user_model,
                 coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None):
        self.IO_LIBRARY = io_library
        self.ENTITY_MODEL = entity_model
        self.USER_MODEL = user_model
        self.COA_MODEL = coa_model
        self.__COMMITTED: bool = False
        self.blueprints = defaultdict(list)
        self.ledger_model_qs: Optional[LedgerModelQuerySet] = None
        self.account_model_qs: Optional[AccountModelQuerySet] = None
        self.ledger_map = dict()
        self.commit_plan = dict()
        self.instructions = None

    def get_ledger_model_qs(self) -> LedgerModelQuerySet:
        return LedgerModel.objects.for_entity(
            self.ENTITY_MODEL,
            self.USER_MODEL
        )

    def get_account_model_qs(self) -> AccountModelQuerySet:
        return self.ENTITY_MODEL.get_coa_accounts(
            coa_model=self.COA_MODEL
        )

    def resolve_account_model_qs(self, codes):
        if self.account_model_qs is None:
            # codes = self.get_account_codes()
            qs = self.get_account_model_qs()
            qs = qs.filter(code__in=codes)
            self.account_model_qs = qs
        return self.account_model_qs

    def resolve_ledger_model_qs(self):
        if self.ledger_model_qs is None:
            qs = self.get_ledger_model_qs()
            by_uuid = [k for k in self.blueprints.keys() if isinstance(k, UUID)]
            by_xid = [k for k in self.blueprints.keys() if isinstance(k, str)]
            self.ledger_model_qs = qs.filter(
                Q(uuid__in=by_uuid) | Q(ledger_xid__in=by_xid)
            )
        return self.ledger_model_qs

    def dispatch(self,
                 name,
                 ledger_model: Optional[Union[str, LedgerModel, UUID]] = None,
                 **kwargs):

        if not isinstance(ledger_model, (str, UUID, LedgerModel)):
            raise IOCursorValidationError(
                message=_('Ledger Model must be a string or UUID or LedgerModel')
            )

        if isinstance(ledger_model, LedgerModel):
            self.ENTITY_MODEL.validate_ledger_model_for_entity(ledger_model)

        blueprint_gen = self.IO_LIBRARY.get_blueprint(name)
        blueprint = blueprint_gen(**kwargs)
        self.blueprints[ledger_model].append(blueprint)

    def compile_instructions(self):

        if self.instructions is None:
            instructions = {
                ledger_model: list(chain.from_iterable(
                    io_blueprint.registry for io_blueprint in instructions
                )) for ledger_model, instructions in self.commit_plan.items()
            }

            for ledger_model, txs in instructions.items():
                total_credits = sum(t.amount for t in txs if t.tx_type == CREDIT)
                total_debits = sum(t.amount for t in txs if t.tx_type == DEBIT)

                # print("{} credits, {} debits".format(total_credits, total_debits))

                if total_credits != total_debits:
                    raise IOCursorValidationError(
                        message=_('Total transactions Credits and Debits must equal: ')
                    )

            self.instructions = instructions
        return self.instructions

    def is_committed(self) -> bool:
        return self.__COMMITTED

    def commit(self,
               je_timestamp: Optional[Union[datetime, date, str]] = None,
               post_new_ledgers: bool = False,
               post_journal_entries: bool = False):
        if self.is_committed():
            raise IOCursorValidationError(
                message=_('Transactions already committed')
            )
        qs = self.resolve_ledger_model_qs()
        self.ledger_map = {l.ledger_xid: l for l in qs if l.ledger_xid} | {l.uuid: l for l in qs}

        # checks for any locked ledgers...
        for k, ledger_model in self.ledger_map.items():
            if ledger_model.is_locked():
                raise IOCursorValidationError(
                    message=_(f'Cannot transact on a locked ledger: {ledger_model}')
                )

        for k, txs in self.blueprints.items():
            if k is None:

                # no specified xid, ledger or UUID... create one...
                self.commit_plan[
                    self.ENTITY_MODEL.create_ledger(
                        name='Blueprint Commitment',
                        commit=False,
                        posted=post_new_ledgers
                    )
                ] = txs

            elif isinstance(k, str):
                try:
                    # ledger with xid already exists...
                    self.commit_plan[self.ledger_map[k]] = txs
                except KeyError:
                    # create ledger with xid provided...
                    self.commit_plan[
                        self.ENTITY_MODEL.create_ledger(
                            name=f'Blueprint Commitment {k}',
                            ledger_xid=k,
                            commit=False,
                            posted=post_new_ledgers
                        )
                    ] = txs

            elif isinstance(k, UUID):
                try:
                    self.commit_plan[self.ledger_map[k]] = txs
                except KeyError:
                    raise IOLibraryError(
                        message=_(f'Ledger UUID {k} not found.')
                    )

            elif isinstance(k, LedgerModel):
                self.commit_plan[k] = txs

            else:
                raise IOLibraryError('Unsupported ledger of type {x}'.format(x=type(k)))

        instructions = self.compile_instructions()
        account_codes = set(tx.account_code for tx in chain.from_iterable(tr for _, tr in instructions.items()))
        account_models = {acc.code: acc for acc in self.resolve_account_model_qs(codes=account_codes)}

        for tx in chain.from_iterable(tr for _, tr in instructions.items()):
            tx.account_model = account_models[tx.account_code]

        results = dict()
        for ledger_model, tr_items in instructions.items():
            if ledger_model._state.adding:
                ledger_model.save()
            je_txs = [t.to_dict() for t in tr_items]

            # where the magic happens...
            je, txs_models = ledger_model.commit_txs(
                je_timestamp=je_timestamp if je_timestamp else get_localtime(),
                je_txs=je_txs,
                je_posted=post_journal_entries
            )

            results[ledger_model] = {
                'journal_entry': je,
                'txs_models': txs_models,
                'instructions': tr_items
            }
        results['account_model_qs'] = self.account_model_qs
        self.__COMMITTED = True
        return results


class IOLibraryError(ValidationError):
    pass


class IOBluePrintValidationError(ValidationError):
    pass


class IOBluePrint:

    def __init__(self, precision_decimals: int = 2):
        self.precision_decimals = precision_decimals
        self.registry = list()

    def _round_amount(self, amount: Decimal) -> Decimal:
        return round(amount, self.precision_decimals)

    def _amount(self, amount: Union[float, Decimal]) -> Decimal:
        if amount <= 0:
            raise IOBluePrintValidationError(
                message='Amounts must be greater than 0'
            )

        if isinstance(amount, float):
            return self._round_amount(Decimal.from_float(amount))

        elif isinstance(amount, Decimal):
            return self._round_amount(amount)

        raise IOBluePrintValidationError(
            message='Amounts must be float or Decimal'
        )

    def credit(self, account_code: str, amount: Union[float, Decimal], description: str = None):

        self.registry.append(
            TransactionInstructionItem(
                account_code=account_code,
                amount=self._amount(amount),
                tx_type=CREDIT,
                description=description
            ))

    def debit(self, account_code: str, amount: Union[float, Decimal], description: str = None):

        self.registry.append(
            TransactionInstructionItem(
                account_code=account_code,
                amount=self._amount(amount),
                tx_type=DEBIT,
                description=description
            ))


class IOLibrary:

    def __init__(self, name: str):
        self.name = name
        self.registry: Dict[str, Callable] = {}

    def _check_func_name(self, name) -> bool:
        return name in self.registry

    def register(self, func: Callable):
        self.registry[func.__name__] = func

    def get_blueprint(self, name: str) -> Callable:
        if not self._check_func_name(name):
            raise IOLibraryError(message=f'Function "{name}" is not registered in IO library {self.name}')
        return self.registry[name]

    def get_cursor(
            self,
            entity_model: EntityModel,
            user_model,
            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None
    ) -> IOCursor:
        return IOCursor(
            io_library=self,
            entity_model=entity_model,
            user_model=user_model,
            coa_model=coa_model,
        )
