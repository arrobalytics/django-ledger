"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

This module contains classes and functions used to document, dispatch and commit new transaction into the database.
"""
import enum
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import chain
from typing import Union, Dict, Callable, Optional, List, Set
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


class IOCursorMode(enum.Enum):
    STRICT = 'strict'
    PERMISSIVE = 'permissive'


class IOCursor:
    """
    Represents a Django Ledger cursor capable of dispatching transactions to the database.
    The Cursor class is responsible for coordinating the creation of new ledgers, journal entries and transactions
    It is a low level interface to the IOBlueprint and IOLibrary classes.

    Parameters
    ----------
    io_library: IOLibrary
        The IOLibrary class that contains all the necessary instructions to dispatch the transactions.
    entity_model: EntityModel
        The EntityModel instance that will be used for the new transactions.
    user_model: UserModel
        The UserModel instance that will be used for the new transactions. Used for read permissions of QuerySets.
    coa_model: ChartOfAccountModel or UUID or str.
        The ChartOfAccountModel instance that contains the accounts to be used for transactions.
        Instance, UUID or slug can be sued to retrieve the model.
    """

    def __init__(self,
                 io_library,
                 entity_model: EntityModel,
                 user_model,
                 mode: IOCursorMode = IOCursorMode.PERMISSIVE,
                 coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None):
        self.IO_LIBRARY = io_library
        self.MODE = mode
        self.ENTITY_MODEL = entity_model
        self.USER_MODEL = user_model
        self.COA_MODEL = coa_model
        self.blueprints = defaultdict(list)
        self.ledger_model_qs: Optional[LedgerModelQuerySet] = None
        self.account_model_qs: Optional[AccountModelQuerySet] = None
        self.ledger_map = dict()
        self.commit_plan = dict()
        self.instructions = None
        self.__COMMITTED: bool = False

    def get_ledger_model_qs(self) -> LedgerModelQuerySet:
        """
        Determines the ledger model queryset associated with the entity model and user model provided.

        Returns
        -------
        LedgerModelQuerySet
        """
        return LedgerModel.objects.for_entity(
            self.ENTITY_MODEL,
            self.USER_MODEL
        )

    def get_account_model_qs(self) -> AccountModelQuerySet:
        """
        Determines the AccountModelQuerySet associated with the Chart of Accounts specified.

        Returns
        -------
        AccountModelQuerySet
        """
        return self.ENTITY_MODEL.get_coa_accounts(
            coa_model=self.COA_MODEL
        ).can_transact()

    def resolve_account_model_qs(self, codes: Set[str]) -> AccountModelQuerySet:
        """
        Resolves the final AccountModelQuerySet associated with the given account codes used by the blueprint.

        Parameters
        ----------
        codes: List[str]
            List of codes used during the execution of the blueprint.


        Returns
        -------
        AccountModelQuerySet
            The resolved AccountModelQuerySet associated with the given codes.
        """
        if self.account_model_qs is None:
            qs = self.get_account_model_qs()
            qs = qs.filter(code__in=codes)
            self.account_model_qs = qs
        return self.account_model_qs

    def resolve_ledger_model_qs(self) -> LedgerModelQuerySet:
        """
        Resolves the final LedgerModelQuerySet associated with the provided ledger model identifiers used by the
        blueprints.

        Returns
        -------
        LedgerModelQuerySet
            The resolved LedgerModelQuerySet associated with the given ledger model identifiers.
        """
        if self.ledger_model_qs is None:
            qs = self.get_ledger_model_qs()
            by_uuid = [k for k in self.blueprints.keys() if isinstance(k, UUID)]
            by_xid = [k for k in self.blueprints.keys() if isinstance(k, str)]
            self.ledger_model_qs = qs.filter(
                Q(uuid__in=by_uuid) | Q(ledger_xid__in=by_xid)
            )
        return self.ledger_model_qs

    def is_permissive(self) -> bool:
        return self.MODE == IOCursorMode.PERMISSIVE

    def is_strict(self) -> bool:
        return self.MODE == IOCursorMode.STRICT

    def dispatch(self,
                 name,
                 ledger_model: Optional[Union[str, LedgerModel, UUID]] = None,
                 **kwargs):
        """
        Stages the instructions to be processed by the IOCursor class. This method does not commit the transactions
        into the database.

        Parameters
        ----------
        name: str
            The registered blueprint name to be staged.
        ledger_model: Optional[Union[str, LedgerModel, UUID]]
            Optional ledger model identifier to house the transactions associated with the blueprint. If none is
            provided, a new ledger model will be created.
        kwargs
            The keyword arguments to be passed to the blueprint function.
        """

        if ledger_model is not None:
            if not isinstance(ledger_model, (str, UUID, LedgerModel)):
                raise IOCursorValidationError(
                    message=_('Ledger Model must be a string or UUID or LedgerModel')
                )

            if isinstance(ledger_model, LedgerModel):
                self.ENTITY_MODEL.validate_ledger_model_for_entity(ledger_model)

        blueprint_func = self.IO_LIBRARY.get_blueprint(name)
        blueprint_txs = blueprint_func(**kwargs)
        self.blueprints[ledger_model].append(blueprint_txs)

    def compile_instructions(self) -> Dict:
        """
        Compiles the blueprint instructions into Journal Entries and Transactions to be committed to the ledger.

        Returns
        -------
        Dict
            A dictionary containing the compiled instructions.
        """
        if self.instructions is None:
            instructions = {
                ledger_model: list(chain.from_iterable(
                    io_blueprint.registry for io_blueprint in instructions
                )) for ledger_model, instructions in self.commit_plan.items()
            }

            for ledger_model, txs in instructions.items():
                total_credits = sum(t.amount for t in txs if t.tx_type == CREDIT)
                total_debits = sum(t.amount for t in txs if t.tx_type == DEBIT)

                if total_credits != total_debits:
                    raise IOCursorValidationError(
                        message=_('Total transactions Credits and Debits must be equal. '
                                  'Got CREDITs: {} and DEBITs: {}.'.format(total_credits, total_debits))
                    )

            self.instructions = instructions
        return self.instructions

    def is_committed(self) -> bool:
        """
        Determines if the IOCursor instance has committed the transactions into the database.
        A cursor can only commit transactions once.

        Returns
        -------
        bool
            True if committed, False otherwise.
        """
        return self.__COMMITTED

    def commit(self,
               je_timestamp: Optional[Union[datetime, date, str]] = None,
               je_description: Optional[str] = None,
               post_new_ledgers: bool = False,
               post_journal_entries: bool = False,
               **kwargs):

        """
        Commits the compiled blueprint transactions into the database. This action is irreversible and if journal
        entries are posted, the books will be immediately impacted by the new transactions. It is encouraged NOT to
        post anything until the transaction is reviews for accuracy.

        Parameters
        ----------
        je_timestamp: Optional[Union[datetime, date, str]]
            The date or timestamp used for the committed journal entries. If none, localtime will be used.
        je_description: Optional[str]
            The description of the journal entries. If none, no description will be used.
        post_new_ledgers: bool
            If a new ledger is created, the ledger model will be posted to the database.
        post_journal_entries: bool
            If new journal entries are created, the journal entry models will be posted to the database.
        kwargs
            Additional keyword arguments passed to the IO commit_txs function.
        """
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

                if self.is_permissive():
                    # no specified xid, ledger or UUID... create one...
                    self.commit_plan[
                        self.ENTITY_MODEL.create_ledger(
                            name='Blueprint Commitment',
                            commit=False,
                            posted=post_new_ledgers
                        )
                    ] = txs
                else:
                    raise IOCursorValidationError(
                        message=_('Cannot commit transactions to a non-existing ledger')
                    )

            elif isinstance(k, str):
                try:
                    # ledger with xid already exists...
                    self.commit_plan[self.ledger_map[k]] = txs
                except KeyError:
                    if self.is_permissive():
                        # create ledger with xid provided...
                        self.commit_plan[
                            self.ENTITY_MODEL.create_ledger(
                                name=f'Blueprint Commitment {k}',
                                ledger_xid=k,
                                commit=False,
                                posted=post_new_ledgers
                            )
                        ] = txs
                    else:
                        raise IOCursorValidationError(
                            message=_(f'Cannot commit transactions to a non-existing ledger_xid {k}')
                        )

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
        account_model_qs = self.resolve_account_model_qs(codes=account_codes)
        account_models = {
            acc.code: acc for acc in account_model_qs
        }

        for tx in chain.from_iterable(tr for _, tr in instructions.items()):
            try:
                tx.account_model = account_models[tx.account_code]
            except KeyError:
                raise IOCursorValidationError(
                    message=_(f'Account code {tx.account_code} not found. Is account available and not locked?')
                )

        results = dict()
        for ledger_model, tr_items in instructions.items():
            if ledger_model._state.adding:
                ledger_model.save()
            je_txs = [t.to_dict() for t in tr_items]

            # where the magic happens...
            je, txs_models = ledger_model.commit_txs(
                je_timestamp=je_timestamp if je_timestamp else get_localtime(),
                je_txs=je_txs,
                je_posted=post_journal_entries,
                je_desc=je_description,
                **kwargs
            )

            je.txs_models = txs_models

            results[ledger_model] = {
                'ledger_model': ledger_model,
                'journal_entry': je,
                'txs_models': txs_models,
                'instructions': tr_items,
                'account_model_qs': self.account_model_qs
            }

        self.__COMMITTED = True
        return results


class IOLibraryError(ValidationError):
    pass


class IOBluePrintValidationError(ValidationError):
    pass


class IOBluePrint:
    """
    This class documents instructions required to assemble and dispatch transactions into the ledger.

    Parameters
    ----------
    name: str, optional
        The human-readable name of the IOBluePrint instance.
    precision_decimals: int
        The number of decimals to use when balancing transactions. Defaults to 2.
    """

    def __init__(self, name: Optional[str] = None, precision_decimals: int = 2):
        self.name = name
        self.precision_decimals = precision_decimals
        self.registry = list()

    def get_name(self, entity_model: EntityModel) -> str:
        """
        Determines the name of the blueprint if none provided.

        Parameters
        ----------
        entity_model: EntityModel
            The EntityModel instance where the resulting blueprint transactions will be stored.

        Returns
        -------
        str
            The name of the blueprint.
        """
        if self.name is None:
            l_dt = get_localtime()
            return f'blueprint-{entity_model.slug}-{l_dt.strftime("%m%d%Y-%H%M%S")}'
        return self.name

    def _round_amount(self, amount: Decimal) -> Decimal:
        return round(amount, self.precision_decimals)

    def _amount(self, amount: Union[float, Decimal, int]) -> Decimal:
        if amount <= 0:
            raise IOBluePrintValidationError(
                message='Amounts must be greater than 0'
            )

        if isinstance(amount, float):
            return self._round_amount(Decimal.from_float(amount))

        elif isinstance(amount, Decimal):
            return self._round_amount(amount)

        elif isinstance(amount, int):
            return Decimal(str(amount))

        raise IOBluePrintValidationError(
            message='Amounts must be float or Decimal'
        )

    def credit(self, account_code: str, amount: Union[float, Decimal], description: str = None):
        """
        Registers a CREDIT to the specified account..

        Parameters
        ----------
        account_code: str
            The account code to use for the transaction.
        amount: float or Decimal
            The amount of the transaction.
        description: str
            Description of the transaction.
        """
        self.registry.append(
            TransactionInstructionItem(
                account_code=account_code,
                amount=self._amount(amount),
                tx_type=CREDIT,
                description=description
            ))

    def debit(self, account_code: str, amount: Union[float, Decimal], description: str = None):
        """
        Registers a DEBIT to the specified account.

        Parameters
        ----------
        account_code: str
            The account code to use for the transaction.
        amount: float or Decimal
            The amount of the transaction.
        description: str
            Description of the transaction.
        """
        self.registry.append(
            TransactionInstructionItem(
                account_code=account_code,
                amount=self._amount(amount),
                tx_type=DEBIT,
                description=description
            ))

    def commit(self,
               entity_model: EntityModel,
               user_model,
               ledger_model: Optional[Union[str, LedgerModel, UUID]] = None,
               je_timestamp: Optional[Union[datetime, date, str]] = None,
               post_new_ledgers: bool = False,
               post_journal_entries: bool = False,
               **kwargs) -> Dict:
        """
        Commits the blueprint transactions to the database.

        Parameters
        ----------
        entity_model: EntityModel
            The entity model instance where transactions will be committed.
        user_model: UserModel
            The user model instance executing transactions to check for permissions.
        ledger_model: Optional[Union[str, LedgerModel, UUID]]
            The ledger model instance identifier to be used for the transactions. If none, a new ledger will be created.
        je_timestamp: date or datetime or str, optional
            The date and/or time to be used for the transactions. If none, localtime will be used.
        post_new_ledgers: bool
            If True, newly created ledgers will be posted. Defaults to False.
        post_journal_entries: bool
            If True, newly created journal entries will be posted. Defaults to False.
        kwargs
            Keyword arguments passed to the IO Library.

        Returns
        -------
        Dict
            A dictionary containing the resulting models of the transactions.
        """
        blueprint_lib = IOLibrary(
            name=self.get_name(
                entity_model=entity_model
            ))

        cursor = blueprint_lib.get_cursor(
            entity_model=entity_model,
            user_model=user_model
        )

        cursor.blueprints[ledger_model].append(self)

        return cursor.commit(
            je_timestamp=je_timestamp,
            post_new_ledgers=post_new_ledgers,
            post_journal_entries=post_journal_entries,
            **kwargs
        )


class IOLibrary:
    """
    The IO Library is a centralized interface for documenting commonly used operations. The library will register and
    document the blueprints and their instructions so that they can be dispatched from anywhere in the application.

    Parameters
    ----------
    name: str
        The human-readable name of the library (i.e. PayRoll, Expenses, Rentals, etc...)
    """

    IO_CURSOR_CLASS = IOCursor

    def __init__(self, name: str):
        self.name = name
        self.registry: Dict[str, Callable] = {}

    def _check_func_name(self, name) -> bool:
        return name in self.registry

    def register(self, func: Callable):
        self.registry[func.__name__] = func

    def get_blueprint(self, name: str) -> Callable:
        """
        Retrieves a blueprint by name.

        Parameters
        ----------
        name: str
            The name of the blueprint to retrieve.

        Returns
        -------
        Callable
        """
        if not self._check_func_name(name):
            raise IOLibraryError(message=f'Function "{name}" is not registered in IO library {self.name}')
        return self.registry[name]

    def get_io_cursor_class(self):
        return self.IO_CURSOR_CLASS

    def get_cursor(
            self,
            entity_model: EntityModel,
            user_model,
            mode: IOCursorMode = IOCursorMode.PERMISSIVE,
            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None
    ) -> IOCursor:
        """
        Creates a cursor instance for associated with the library, entity and user model.

        Parameters
        ----------
        entity_model: EntityModel
            The entity model instance where transactions will be committed.
        user_model: UserModel
            The user model instance executing the transactions.
        coa_model: ChartOfAccountModel or UUID or str, optional
            The ChartOfAccountsModel instance or identifier used to determine the AccountModelQuerySet used for the transactions.
        mode: IOCursorMode
            The Mode of the cursor instance. Defaults to IOCursorMode.PERMISSIVE.

        Returns
        -------
        IOCursor
        """
        io_cursor_class = self.get_io_cursor_class()
        return io_cursor_class(
            io_library=self,
            entity_model=entity_model,
            user_model=user_model,
            coa_model=coa_model,
            mode=mode
        )
