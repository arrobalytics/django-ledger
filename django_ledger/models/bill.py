"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

This module implements the BillModel, which represents an Invoice received from a Supplier/Vendor, on which
the Vendor states the amount owed by the recipient for the purposes of supplying goods and/or services.
In addition to tracking the bill amount, it tracks the paid and due amount.

Examples
________
>>> user_model = request.user  # django UserModel
>>> entity_slug = kwargs['entity_slug'] # may come from view kwargs
>>> bill_model = BillModel()
>>> ledger_model, bill_model = bill_model.configure(entity_slug=entity_slug, user_model=user_model)
>>> bill_model.save()
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Union, Optional, Tuple, Dict, List
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, F, Count
from django.db.models.signals import post_delete, pre_save
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate, localtime
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModelQuerySet, ItemTransactionModel, ItemModel, ItemModelQuerySet
from django_ledger.models.mixins import (CreateUpdateMixIn, AccrualMixIn, MarkdownNotesMixIn,
                                         PaymentTermsMixIn, ItemizeMixIn)
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_BILL_NUMBER_PREFIX)

UserModel = get_user_model()


class BillModelValidationError(ValidationError):
    pass


class BillModelQuerySet(models.QuerySet):
    """
    A custom defined QuerySet for the BillModel. This implements multiple methods or queries needed to get a filtered
    QuerySet based on the BillModel status. For example, we might want to have list of bills which are paid, unpaid,
    due ,overdue, approved or in draft stage. All these separate functions will assist in making such queries and
    building customized reports.
    """

    def draft(self):
        """
        Default status of any bill that is created.
        Draft bills do not impact the Ledger.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of draft bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_DRAFT)

    def in_review(self):
        """
        In review bills are those that need additional review or approvals before being approved.
        In review bills do not impact the Ledger.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of bills in review only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_REVIEW)

    def approved(self):
        """
        Approved bills are those that have been reviewed and are expected to be paid before the due date.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of approved bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_APPROVED)

    def paid(self):
        """
        Paid bills are those that have received 100% of the amount due.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of paid bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_PAID)

    def void(self):
        """
        Void bills are those that where rolled back after being approved.
        Void bills rollback all transactions by creating a new set of transactions posted on the date_void.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of void bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_VOID)

    def canceled(self):
        """
        Canceled bills are those that are discarded during the draft or in review status.
        These bills never had an impact on the books.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of canceled bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_CANCELED)

    def active(self):
        """
        Active bills are those that are approved or paid, which have
        impacted or have the potential to impact the Entity's Ledgers.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of active bills only.
        """
        return self.filter(
            Q(bill_status__exact=BillModel.BILL_STATUS_APPROVED) |
            Q(bill_status__exact=BillModel.BILL_STATUS_PAID)
        )

    def overdue(self):
        """
        Overdue bills are those which due date is in the past.

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of overdue bills only.
        """
        return self.filter(date_due__lt=localdate())

    def unpaid(self):
        """
        Unpaid bills are those that are approved but have not received 100% of the amount due.
        Equivalent to approved().

        Returns
        -------
        BillModelQuerySet
            Returns a QuerySet of paid bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_APPROVED)


class BillModelManager(models.Manager):
    """
    A custom defined BillModelManager that will act as an interface to handling the initial DB queries
    to the BillModel. The default "get_queryset" has been overridden to refer the custom defined
    "BillModelQuerySet".
    """

    def for_user(self, user_model) -> BillModelQuerySet:
        """
        Fetches a QuerySet of BillModels that the UserModel as access to.
        May include BillModels from multiple Entities.

        The user has access to bills if:
            1. Is listed as Manager of Entity.
            2. Is the Admin of the Entity.

        Parameters
        __________
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = request.user
            >>> bill_model_qs = BillModel.objects.for_user(user_model=request_user)

        Returns
        _______
        BillModelQuerySet
            Returns a BillModelQuerySet with applied filters.
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model) -> BillModelQuerySet:
        """
        Fetches a QuerySet of BillModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> bill_model_qs = BillModel.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        _______
        BillModelQuerySet
            Returns a BillModelQuerySet with applied filters.
        """
        qs = self.get_queryset()
        if isinstance(entity_slug, EntityModel):
            return qs.filter(
                Q(ledger__entity=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )
        elif isinstance(entity_slug, str):
            return qs.filter(
                Q(ledger__entity__slug__exact=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )


class BillModelAbstract(AccrualMixIn,
                        ItemizeMixIn,
                        PaymentTermsMixIn,
                        MarkdownNotesMixIn,
                        CreateUpdateMixIn):
    """
    This is the main abstract class which the BillModel database will inherit from.
    The BillModel inherits functionality from the following MixIns:

        1. :func:`LedgerWrapperMixIn <django_ledger.models.mixins.LedgerWrapperMixIn>`
        2. :func:`PaymentTermsMixIn <django_ledger.models.mixins.PaymentTermsMixIn>`
        3. :func:`MarkdownNotesMixIn <django_ledger.models.mixins.MarkdownNotesMixIn>`
        4. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`

    Attributes
    ----------
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    bill_number: str
        Auto assigned number at creation by generate_bill_number() function.
        Prefix be customized with DJANGO_LEDGER_BILL_NUMBER_PREFIX setting.
        Includes a reference to the Fiscal Year and a sequence number. Max Length is 20.

    bill_status: str
        Current status of the BillModel. Must be one of the choices as mentioned under "BILL_STATUS".
        By default , the status will be "Draft". Options are: Draft, In Review, Approved, Paid, Void or Canceled.

    xref: str
        This is the filed for capturing of any External reference number like the PO number of the buyer.
        Any other reference number like the Vendor code in buyer books may also be captured.

    vendor: :obj:`VendorModel`
        This is the foreign key reference to the VendorModel from whom the purchase has been made.

    additional_info: dict
        Any additional metadata about the BillModel may be stored here as a dictionary object.
        The data is serialized and stored as a JSON document in the Database.

    bill_items:
        A foreign key reference to the list of ItemTransactionModel that make the bill amount.

    ce_model: EstimateModel
        A foreign key to the BillModel associated EstimateModel for overall Job/Contract tracking.

    date_draft: date
        The draft date represents the date when the BillModel was first created. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.

    date_in_review: date
        The in review date represents the date when the BillModel was marked as In Review status.
        Will be null if BillModel is canceled during draft status. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.

    date_approved: date
        The approved date represents the date when the BillModel was approved. Will be null if BillModel is canceled.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.

    date_paid: date
        The paid date represents the date when the BillModel was paid and amount_due equals amount_paid.
        Will be null if BillModel is canceled. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.

    date_void: date
        The void date represents the date when the BillModel was void, if applicable.
        Will be null unless BillModel is void. Defaults to :func:`localdate <django.utils.timezone.localdate>`.

    date_canceled: date
        The canceled date represents the date when the BillModel was canceled, if applicable.
        Will be null unless BillModel is canceled. Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    """
    REL_NAME_PREFIX = 'bill'
    IS_DEBIT_BALANCE = False
    ALLOW_MIGRATE = True

    BILL_STATUS_DRAFT = 'draft'
    BILL_STATUS_REVIEW = 'in_review'
    BILL_STATUS_APPROVED = 'approved'
    BILL_STATUS_PAID = 'paid'
    BILL_STATUS_VOID = 'void'
    BILL_STATUS_CANCELED = 'canceled'

    BILL_STATUS = [
        (BILL_STATUS_DRAFT, _('Draft')),
        (BILL_STATUS_REVIEW, _('In Review')),
        (BILL_STATUS_APPROVED, _('Approved')),
        (BILL_STATUS_PAID, _('Paid')),
        (BILL_STATUS_CANCELED, _('Canceled')),
        (BILL_STATUS_VOID, _('Void'))
    ]
    """
    The different bill status options and their representation in the Database.
    """

    # todo: implement Void Bill (& Invoice)....
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    bill_number = models.SlugField(max_length=20, verbose_name=_('Bill Number'), editable=False)
    bill_status = models.CharField(max_length=10,
                                   choices=BILL_STATUS,
                                   default=BILL_STATUS[0][0],
                                   verbose_name=_('Bill Status'))
    xref = models.SlugField(null=True, blank=True, verbose_name=_('External Reference Number'))
    vendor = models.ForeignKey('django_ledger.VendorModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor'))
    additional_info = models.JSONField(blank=True,
                                       null=True,
                                       default=dict,
                                       verbose_name=_('Bill Additional Info'))
    bill_items = models.ManyToManyField('django_ledger.ItemModel',
                                        through='django_ledger.ItemTransactionModel',
                                        through_fields=('bill_model', 'item_model'),
                                        verbose_name=_('Bill Items'))

    ce_model = models.ForeignKey('django_ledger.EstimateModel',
                                 on_delete=models.RESTRICT,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Associated Customer Job/Estimate'))

    date_draft = models.DateField(null=True, blank=True, verbose_name=_('Draft Date'))
    date_in_review = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    date_approved = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    date_paid = models.DateField(null=True, blank=True, verbose_name=_('Paid Date'))
    date_void = models.DateField(null=True, blank=True, verbose_name=_('Void Date'))
    date_canceled = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

    objects = BillModelManager.from_queryset(queryset_class=BillModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Bill')
        verbose_name_plural = _('Bills')
        indexes = [
            models.Index(fields=['bill_status']),
            models.Index(fields=['terms']),

            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),

            models.Index(fields=['date_due']),
            models.Index(fields=['date_draft']),
            models.Index(fields=['date_in_review']),
            models.Index(fields=['date_approved']),
            models.Index(fields=['date_paid']),
            models.Index(fields=['date_canceled']),
            models.Index(fields=['date_void']),

            models.Index(fields=['vendor']),
            models.Index(fields=['bill_number']),
        ]

    def __str__(self):
        return f'Bill: {self.bill_number}'

    def is_configured(self) -> bool:
        return all([
            super().is_configured(),
            self.bill_status
        ])

    # Configuration...
    def configure(self,
                  entity_slug: Union[str, EntityModel],
                  user_model: Optional[UserModel] = None,
                  date_draft: Optional[date] = None,
                  ledger_posted: bool = False,
                  ledger_name: str = None,
                  commit: bool = False,
                  commit_ledger: bool = False):
        """
        A configuration hook which executes all initial BillModel setup on to the LedgerModel and all initial
        values of the BillModel. Can only call this method once in the lifetime of a BillModel.

        Parameters
        ----------

        date_draft: date
            Optional date to use as Draft Date. Defaults to localdate() if None.
        entity_slug: str or EntityModel
            The entity slug or EntityModel to associate the Bill with.
        user_model: UserModel
            The UserModel making the request to check for QuerySet permissions.
        ledger_posted: bool
            An option to mark the BillModel Ledger as posted at the time of configuration. Defaults to False.
        ledger_name: str
            Optional additional InvoiceModel ledger name or description.
        commit: bool
            Saves the current BillModel after being configured.
        commit_ledger: bool
            Saves the BillModel's LedgerModel while being configured.

        Returns
        -------
        A tuple of LedgerModel, BillModel
        """

        # todo: add raise_exception flag, check if this is consistent...

        if not self.is_configured():
            if isinstance(entity_slug, str):
                if not user_model:
                    raise BillModelValidationError(_('Must pass user_model when using entity_slug.'))
                entity_qs = EntityModel.objects.for_user(user_model=user_model)
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
            elif isinstance(entity_slug, EntityModel):
                entity_model = entity_slug
            else:
                raise BillModelValidationError('entity_slug must be an instance of str or EntityModel')

            if entity_model.is_accrual_method():
                self.accrue = True
                self.progress = Decimal.from_float(1.00)
            else:
                self.accrue = False

            self.bill_status = self.BILL_STATUS_DRAFT
            self.date_draft = localdate() if not date_draft else date_draft

            LedgerModel = lazy_loader.get_ledger_model()
            ledger_model: LedgerModel = LedgerModel(entity=entity_model, posted=ledger_posted)
            ledger_name = f'Bill {self.uuid}' if not ledger_name else ledger_name
            ledger_model.name = ledger_name
            ledger_model.configure_for_wrapper_model(model_instance=self)
            ledger_model.clean()
            ledger_model.clean_fields()
            self.ledger = ledger_model

            if commit_ledger:
                self.ledger.save()

            if self.can_generate_bill_number():
                self.generate_bill_number(commit=commit)

            self.clean()
            self.clean_fields()

            if commit:
                self.save()

        return self.ledger, self

    # ### ItemizeMixIn implementation START...
    def can_migrate_itemtxs(self) -> bool:
        return self.is_draft()

    def migrate_itemtxs(self, itemtxs: Dict, operation: str, commit: bool = False):
        itemtxs_batch = super().migrate_itemtxs(itemtxs=itemtxs, commit=commit, operation=operation)
        self.update_amount_due(itemtxs_qs=itemtxs_batch)
        self.get_state(commit=True)

        if commit:
            self.save(update_fields=['amount_due',
                                     'amount_receivable',
                                     'amount_unearned',
                                     'amount_earned',
                                     'updated'])
        return itemtxs_batch

    def get_item_model_qs(self) -> ItemModelQuerySet:
        return ItemModel.objects.filter(
            entity_id__exact=self.ledger.entity_id
        ).bills()

    def validate_itemtxs_qs(self, queryset: Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]]):
        """
        Validates that the entire ItemTransactionModelQuerySet is bound to the BillModel.

        Parameters
        ----------
        queryset: ItemTransactionModelQuerySet or list of ItemTransactionModel.
            ItemTransactionModelQuerySet to validate.
        """
        valid = all([
            i.bill_model_id == self.uuid for i in queryset
        ])
        if not valid:
            raise BillModelValidationError(f'Invalid queryset. All items must be assigned to Bill {self.uuid}')

    def get_itemtxs_data(self,
                         queryset: Optional[ItemTransactionModelQuerySet] = None,
                         aggregate_on_db: bool = False,
                         lazy_agg: bool = False) -> Tuple[ItemTransactionModelQuerySet, Dict]:
        """
        Fetches the BillModel Items and aggregates the QuerySet.

        Parameters
        ----------
        queryset:
            Optional pre-fetched ItemModelQueryset to use. Avoids additional DB query if provided.
        aggregate_on_db: bool
            If True, performs aggregation of ItemsTransactions in the DB resulting in one additional DB query.
        Returns
        -------
        A tuple: ItemTransactionModelQuerySet, dict
        """
        if not queryset:
            queryset = self.itemtransactionmodel_set.all().select_related(
                'item_model',
                'entity_unit',
                'po_model',
                'bill_model')
        else:
            self.validate_itemtxs_qs(queryset)

        if aggregate_on_db and isinstance(queryset, ItemTransactionModelQuerySet):
            return queryset, queryset.aggregate(
                total_amount__sum=Sum('total_amount'),
                total_items=Count('uuid')
            )
        return queryset, {
            'total_amount__sum': sum(i.total_amount for i in queryset),
            'total_items': len(queryset)
        } if not lazy_agg else None

    # ### ItemizeMixIn implementation END...

    # State..
    def get_migrate_state_desc(self) -> str:
        """
        Description used when migrating transactions into the LedgerModel.

        Returns
        _______
        str
            Description as a string.
        """
        return f'Bill {self.bill_number} account adjustment.'

    def get_migration_data(self,
                           queryset: Optional[ItemTransactionModelQuerySet] = None) -> ItemTransactionModelQuerySet:
        """
        Fetches necessary item transaction data to perform a migration into the LedgerModel.

        Parameters
        ----------
        queryset: ItemTransactionModelQuerySet
            Optional pre-fetched ItemModelTransactionQueryset to use. Avoids additional DB query if provided.
        """

        if not queryset:
            queryset = self.itemtransactionmodel_set.all()
        else:
            self.validate_itemtxs_qs(queryset)

        return queryset.order_by('item_model__expense_account__uuid',
                                 'entity_unit__uuid',
                                 'item_model__expense_account__balance_type').values(
            'item_model__expense_account__uuid',
            'item_model__inventory_account__uuid',
            'item_model__expense_account__balance_type',
            'item_model__inventory_account__balance_type',
            'entity_unit__slug',
            'entity_unit__uuid',
            'total_amount').annotate(
            account_unit_total=Sum('total_amount')
        )

    def update_amount_due(self,
                          itemtxs_qs: Optional[Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]]] = None
                          ) -> ItemTransactionModelQuerySet:
        """
        Updates the BillModel amount due.

        Parameters
        ----------
        itemtxs_qs: ItemTransactionModelQuerySet or list of ItemTransactionModel
            Optional pre-fetched ItemTransactionModelQuerySet. Avoids additional DB if provided.
            Queryset is validated if provided.

        Returns
        -------
        ItemTransactionModelQuerySet
            Newly fetched of previously fetched ItemTransactionModelQuerySet if provided.
        """
        itemtxs_qs, itemtxs_agg = self.get_itemtxs_data(queryset=itemtxs_qs)
        self.amount_due = round(itemtxs_agg['total_amount__sum'], 2)
        return itemtxs_qs

    def is_draft(self) -> bool:
        """
        Checks if the BillModel is in Draft status.

        Returns
        _______
        bool
            True if BillModel is Draft, else False.
        """
        return self.bill_status == self.BILL_STATUS_DRAFT

    def is_review(self) -> bool:
        """
        Checks if the BillModel is In Review status.

        Returns
        _______
        bool
            True if BillModel is in Review, else False.
        """
        return self.bill_status == self.BILL_STATUS_REVIEW

    def is_approved(self) -> bool:
        """
        Checks if the BillModel is in Approved status.

        Returns
        _______
        bool
            True if BillModel is Approved, else False.
        """
        return self.bill_status == self.BILL_STATUS_APPROVED

    def is_paid(self) -> bool:
        """
        Checks if the BillModel is in Paid status.

        Returns
        _______
        bool
            True if BillModel is Paid, else False.
        """
        return self.bill_status == self.BILL_STATUS_PAID

    def is_canceled(self) -> bool:
        """
        Checks if the BillModel is in Canceled status.

        Returns
        _______
        bool
            True if BillModel is Canceled, else False.
        """
        return self.bill_status == self.BILL_STATUS_CANCELED

    def is_active(self):
        """
        Checks if the BillModel has the potential to impact the books and produce financial statements status.

        Returns
        _______
        bool
            True if BillModel is Active, else False.
        """
        return any([
            self.is_paid(),
            self.is_approved(),
            self.is_void()
        ])

    def is_void(self) -> bool:
        """
        Checks if the BillModel is in Void status.

        Returns
        _______
        bool
            True if BillModel is Void, else False.
        """
        return self.bill_status == self.BILL_STATUS_VOID

    def is_past_due(self) -> bool:
        """
        Checks if the BillModel is past due.

        Returns
        -------
        bool
            True if BillModel is past due, else False.
        """
        if self.date_due and self.is_approved():
            return self.date_due < localdate()
        return False

    # Permissions....
    def can_draft(self) -> bool:
        """
        Checks if the BillModel can be marked as Draft.

        Returns
        -------
        bool
            True if BillModel can be marked as draft, else False.
        """
        return self.is_review()

    def can_review(self) -> bool:
        """
        Checks if the BillModel can be marked as In Review.

        Returns
        -------
        bool
            True if BillModel can be marked as in review, else False.
        """
        return all([
            self.is_configured(),
            self.is_draft()
        ])

    def can_approve(self) -> bool:
        """
        Checks if the BillModel can be marked as Approved.

        Returns
        -------
        bool
            True if BillModel can be marked as approved, else False.
        """
        return self.is_review()

    def can_pay(self) -> bool:
        """
        Checks if the BillModel can be marked as Paid.

        Returns
        -------
        bool
            True if BillModel can be marked as paid, else False.
        """
        return self.is_approved()

    def can_delete(self) -> bool:
        """
        Checks if the BillModel can be deleted.

        Returns
        -------
        bool
            True if BillModel can be deleted, else False.
        """
        return any([
            self.is_review(),
            self.is_draft()
        ])

    def can_void(self) -> bool:
        """
        Checks if the BillModel can be marked as Void status.

        Returns
        -------
        bool
            True if BillModel can be marked as void, else False.
        """
        return self.is_approved()

    def can_cancel(self) -> bool:
        """
        Checks if the BillModel can be marked as Canceled status.

        Returns
        -------
        bool
            True if BillModel can be marked as canceled, else False.
        """
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self) -> bool:
        """
        Checks if the BillModel item transactions can be edited.

        Returns
        -------
        bool
            True if BillModel items can be edited, else False.
        """
        return self.is_draft()

    def can_migrate(self) -> bool:
        """
        Checks if the BillModel can be migrated.

        Returns
        -------
        bool
            True if BillModel can be migrated, else False.
        """
        if not self.is_approved():
            return False
        return super(BillModelAbstract, self).can_migrate()

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        """
        Checks if the BillModel can be bound to a given EstimateModel.

        Parameters
        __________

        estimate_model: EstimateModel
            EstimateModel to check against.

        raise_exception: bool
            If True, raises BillModelValidationError if unable to bind. Else, returns False.

        Returns
        _______

        bool
            True if can bind provided EstimateModel, else False.
        """
        if self.ce_model_id:
            if raise_exception:
                raise BillModelValidationError(f'Bill {self.bill_number} already bound to '
                                               f'Estimate {self.ce_model.estimate_number}')
            return False

        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise BillModelValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    def can_bind_po(self, po_model, raise_exception: bool = False) -> bool:
        """
        Checks if the BillModel can be bound to a given PurchaseOrderModel.

        Parameters
        __________

        po_model: PurchaseOrderModel
            The PurchaseOrderModel to check against.

        raise_exception: bool
            If True, raises BillModelValidationError if unable to bind, else False.

        Returns
        _______

        bool
            True if can bind provided PurchaseOderModel, else False.
        """
        if not po_model.is_approved():
            if raise_exception:
                raise BillModelValidationError(f'Cannot bind an unapproved PO.')
            return False

        if po_model.date_approved > self.date_draft:
            if raise_exception:
                raise BillModelValidationError(f'Approved PO date cannot be greater than Bill draft date.')
            return False

        return True

    def can_generate_bill_number(self) -> bool:
        """
        Checks if BillModel can generate its Document Number.

        Returns
        _______

        bool
            True if BillModel can generate its bill_number, else False.
        """
        return all([
            not self.bill_number,
            self.is_draft(),
            self.is_configured()
        ])

    # ACTIONS ---

    def can_make_payment(self) -> bool:
        """
        Checks if the BillModel can accept a payment.


        Returns
        _______

        bool
            True if can bind provided PurchaseOderModel, else False.
        """
        return self.is_approved()

    def make_payment(self,
                     payment_amount: Union[Decimal, float, int],
                     payment_date: Optional[Union[datetime, date]] = None,
                     commit: bool = False,
                     raise_exception: bool = True):
        """
        Makes a payment to the BillModel.


        Parameters
        __________

        payment_amount: Decimal ot float
            The payment amount to process.

        payment_date: datetime or date.
            Date or timestamp of the payment being applied.

        commit: bool
            If True, commits the transaction into the DB. Defaults to False.

        raise_exception: bool
            If True, raises BillModelValidationError if payment exceeds amount due, else False.

        Returns
        _______

        bool
            True if can make payment, else False.
        """

        if isinstance(payment_amount, float):
            payment_amount = Decimal.from_float(payment_amount)
        elif isinstance(payment_amount, int):
            payment_amount = Decimal.from_float(float(payment_amount))
        self.amount_paid += payment_amount

        if self.amount_paid > self.amount_due:
            if raise_exception:
                raise BillModelValidationError(
                    f'Amount paid: {self.amount_paid} exceed amount due: {self.amount_due}.'
                )
            return

        self.get_state(commit=True)
        self.clean()

        if not payment_date:
            payment_date = localtime()

        if commit:
            self.migrate_state(
                user_model=None,
                entity_slug=self.ledger.entity.slug,
                je_timestamp=payment_date,
                raise_exception=True
            )
            self.save(
                update_fields=[
                    'amount_paid',
                    'amount_earned',
                    'amount_unearned',
                    'amount_receivable',
                    'updated'
                ])

    def bind_estimate(self, estimate_model, commit: bool = False, raise_exception: bool = True):
        """
        Binds BillModel to a given EstimateModel. Raises ValueError if EstimateModel cannot be bound.

        Parameters
        __________
        estimate_model: EstimateModel
            EstimateModel to bind.

        raise_exception: bool
            Raises BillModelValidationError if unable to bind EstimateModel.

        commit: bool
            Commits transaction into current BillModel.
        """
        try:
            self.can_bind_estimate(estimate_model, raise_exception=True)
        except ValueError as e:
            if raise_exception:
                raise e
            return
        self.ce_model = estimate_model
        self.clean()
        if commit:
            self.save(update_fields=[
                'ce_model',
                'updated'
            ])

    def mark_as_draft(self, date_draft: Optional[date] = None, commit: bool = False, **kwargs):
        """
        Marks BillModel as Draft.

        Parameters
        __________

        date_draft: date
            Draft date. If None, defaults to localdate().

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_draft():
            raise BillModelValidationError(
                f'Bill {self.bill_number} cannot be marked as draft. Must be In Review.'
            )
        self.bill_status = self.BILL_STATUS_DRAFT
        self.date_draft = localdate() if not date_draft else date_draft
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'bill_status',
                    'date_draft',
                    'updated'
                ]
            )

    def get_mark_as_draft_html_id(self) -> str:
        """
        BillModel Mark as Draft HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String
        """
        return f'djl-bill-model-{self.uuid}-mark-as-draft'

    def get_mark_as_draft_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Draft action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            HTML ID as a String
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-draft',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_draft_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Draft BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Draft?') % self.bill_number

    # IN REVIEW ACTIONS....
    def mark_as_review(self,
                       commit: bool = False,
                       itemtxs_qs: ItemTransactionModelQuerySet = None,
                       date_in_review: Optional[date] = None,
                       raise_exception: bool = True,
                       **kwargs):
        """
        Marks BillModel as In Review.

        Parameters
        __________

        date_in_review: date
            BillModel in review date. Defaults to localdate() if None.
        itemtxs_qs: ItemTransactionModelQuerySet
            Pre fetched ItemTransactionModelQuerySet to use. Avoids additional DB Query if previously fetched.
        commit: bool
            Commits transaction into the Database. Defaults to False.
        raise_exception: bool
            Raises BillModelValidationError if BillModel cannot be marked as in review. Defaults to True.
        """
        if not self.can_review():
            if raise_exception:
                raise BillModelValidationError(
                    f'Bill {self.bill_number} cannot be marked as in review. Must be Draft and Configured.'
                )

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()
        else:
            self.validate_itemtxs_qs(queryset=itemtxs_qs)

        if not itemtxs_qs.count():
            raise BillModelValidationError(message=f'Cannot review a {self.__class__.__name__} without items...')
        if not self.amount_due:
            raise BillModelValidationError(
                f'Bill {self.bill_number} cannot be marked as in review. Amount due must be greater than 0.'
            )

        self.bill_status = self.BILL_STATUS_REVIEW
        self.date_in_review = localdate() if not date_in_review else date_in_review
        self.date_in_review = date_in_review
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'date_in_review',
                    'bill_status',
                    'updated'
                ]
            )

    def get_mark_as_review_html_id(self) -> str:
        """
        BillModel Mark as In Review HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-review'

    def get_mark_as_review_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Review action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            BillModel mark-as-review action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-review',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_review_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Review BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as In Review?') % self.bill_number

    # APPROVED ACTIONS....
    def mark_as_approved(self,
                         user_model,
                         entity_slug: Optional[str] = None,
                         date_approved: Optional[date] = None,
                         commit: bool = False,
                         force_migrate: bool = False,
                         **kwargs):
        """
        Marks BillModel as Approved.

        Parameters
        __________

        entity_slug
            Entity slug associated with the BillModel. Avoids additional DB query if passed.

        user_model
            UserModel associated with request.

        date_approved: date
            BillModel approved date. Defaults to localdate().

        commit: bool
            Commits transaction into the Database. Defaults to False.

        force_migrate: bool
            Forces migration. True if Accounting Method is Accrual.
        """

        if not self.can_approve():
            raise BillModelValidationError(
                f'Bill {self.bill_number} cannot be marked as in approved.'
            )
        self.bill_status = self.BILL_STATUS_APPROVED
        self.date_approved = localdate() if not date_approved else date_approved
        self.get_state(commit=True)
        self.clean()
        if commit:
            self.save(update_fields=[
                'bill_status',
                'date_approved',
                'date_due',
                'updated'
            ])
            if force_migrate or self.accrue:
                if not entity_slug:
                    entity_slug = self.ledger.entity.slug
                # normally no transactions will be present when marked as approved...
                self.migrate_state(
                    entity_slug=entity_slug,
                    user_model=user_model,
                    je_timestamp=date_approved,
                    force_migrate=self.accrue
                )
            self.ledger.post(commit=commit)

    def get_mark_as_approved_html_id(self) -> str:
        """
        BillModel Mark as Approved HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-approved'

    def get_mark_as_approved_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Approved action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            BillModel mark-as-approved action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-approved',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_approved_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Approved BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Approved?') % self.bill_number

    # PAY ACTIONS....
    def mark_as_paid(self,
                     user_model,
                     entity_slug: Optional[str] = None,
                     date_paid: Optional[date] = None,
                     itemtxs_qs: Optional[ItemTransactionModelQuerySet] = None,
                     commit: bool = False,
                     **kwargs):

        """
        Marks BillModel as Paid.

        Parameters
        __________

        entity_slug: str
            Entity slug associated with the BillModel. Avoids additional DB query if passed.

        user_model:
            UserModel associated with request.

        date_paid: date
            BillModel paid date. Defaults to localdate() if None.

        itemtxs_qs: ItemTransactionModelQuerySet
            Pre-fetched ItemTransactionModelQuerySet. Avoids additional DB query. Validated if passed.

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_pay():
            raise BillModelValidationError(f'Cannot mark Bill {self.bill_number} as paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        self.date_paid = localdate() if not date_paid else date_paid

        if self.date_paid > localdate():
            raise BillModelValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        if self.date_paid < self.date_approved:
            raise BillModelValidationError(
                f'Cannot pay {self.__class__.__name__} before approved date {self.date_approved}.')

        self.bill_status = self.BILL_STATUS_PAID
        self.get_state(commit=True)
        self.clean()

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()
        else:
            self.validate_itemtxs_qs(queryset=itemtxs_qs)

        if commit:
            self.save(update_fields=[
                'date_paid',
                'progress',
                'amount_paid',
                'bill_status',
                'updated'
            ])

            ItemTransactionModel = lazy_loader.get_item_transaction_model()
            itemtxs_qs.filter(
                po_model_id__isnull=False
            ).update(po_item_status=ItemTransactionModel.STATUS_ORDERED)

            if not entity_slug:
                entity_slug = self.ledger.entity.slug

            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                itemtxs_qs=itemtxs_qs,
                je_timestamp=date_paid,
                force_migrate=True
            )
            self.lock_ledger(commit=True)

    def get_mark_as_paid_html_id(self) -> str:
        """
        BillModel Mark as Paid HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String
        """
        return f'djl-bill-model-{self.uuid}-mark-as-paid'

    def get_mark_as_paid_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Paid action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            BillModel mark-as-paid action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_paid_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Paid BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Paid?') % self.bill_number

    # VOID Actions...
    def mark_as_void(self,
                     user_model,
                     entity_slug: Optional[str] = None,
                     date_void: Optional[date] = None,
                     commit: bool = False,
                     **kwargs):
        """
        Marks BillModel as Void.
        When mark as void, all transactions associated with BillModel are reversed as of the void date.

        Parameters
        __________

        entity_slug: str
            Entity slug associated with the BillModel. Avoids additional DB query if passed.

        user_model
            UserModel associated with request.

        date_void: date
            BillModel void date. Defaults to localdate() if None.

        commit: bool
            Commits transaction into DB. Defaults to False.
        """
        if not self.can_void():
            raise BillModelValidationError(f'Bill {self.bill_number} cannot be voided. Must be approved.')

        self.date_void = date_void if date_void else localdate()
        self.bill_status = self.BILL_STATUS_VOID
        self.void_state(commit=True)
        self.clean()

        if commit:
            if not entity_slug:
                entity_slug = self.ledger.entity.slug

            self.unlock_ledger(commit=False, raise_exception=False)
            self.migrate_state(
                entity_slug=entity_slug,
                user_model=user_model,
                void=True,
                void_date=self.date_void,
                raise_exception=False,
                force_migrate=False)
            self.save()
            self.lock_ledger(commit=False, raise_exception=False)

    def get_mark_as_void_html_id(self) -> str:
        """
        BillModel Mark as Void HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-void'

    def get_mark_as_void_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Void action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
            BillModel mark-as-void action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-void',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_void_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Void BillModel confirmation message as a String.
        """
        return _('Do you want to void Bill %s?') % self.bill_number

    # Cancel Actions...
    def mark_as_canceled(self, date_canceled: Optional[date], commit: bool = False, **kwargs):
        """
        Mark BillModel as Canceled.

        Parameters
        __________

        date_canceled: date
            BillModel canceled date. Defaults to localdate() if None.

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_cancel():
            raise BillModelValidationError(f'Bill {self.bill_number} cannot be canceled. Must be draft or in review.')

        self.date_canceled = localdate() if not date_canceled else date_canceled
        self.bill_status = self.BILL_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'bill_status',
                'date_canceled'
            ])

    def get_mark_as_canceled_html_id(self) -> str:
        """
        BillModel Mark as Canceled HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-canceled'

    def get_mark_as_canceled_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Canceled action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            BillModel mark-as-canceled action URL.
        """

        if not entity_slug:
            entity_slug = self.ledger.entity.slug

        return reverse('django_ledger:bill-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Canceled BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Canceled?') % self.bill_number

    # DELETE ACTIONS...
    def mark_as_delete(self, **kwargs):
        """
        Deletes BillModel from DB if possible. Raises exception if can_delete() is False.
        """
        if not self.can_delete():
            raise BillModelValidationError(f'Bill {self.bill_number} cannot be deleted. Must be void after Approved.')
        self.delete(**kwargs)

    def get_mark_as_delete_html_id(self) -> str:
        """
        BillModel Mark as Delete HTML ID Tag.

        Returns
        _______

        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-delete'

    def get_mark_as_delete_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Delete action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            BillModel mark-as-delete action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:bill-action-mark-as-delete',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_delete_message(self) -> str:
        """
        Internationalized confirmation message with Bill Number.

        Returns
        _______
        str
            Mark-as-Delete BillModel confirmation message as a String.
        """
        return _('Do you want to delete Bill %s?') % self.bill_number

    def get_status_action_date(self) -> date:
        """
        Current status action date.

        Returns
        _______
        date
            A date. i.e. If status is Approved, return date_approved. If Paid, return date_paid.
        """
        return getattr(self, f'date_{self.bill_status}')

    # HTML Tags...
    def get_document_id(self) -> Optional[str]:
        """
        Human-readable document number. Defaults to bill_number.

        Returns
        _______
        str
            Document Number as a String.
        """
        return self.bill_number

    def get_html_id(self) -> str:
        """
        Unique BillNumber HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}'

    def get_html_amount_due_id(self) -> str:
        """
        Unique amount due HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-amount-due'

    def get_html_amount_paid_id(self) -> str:
        """
        Unique amount paid HTML ID

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-amount-paid'

    def get_html_form_id(self) -> str:
        """
        Unique BillModel Form HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-form'

    def get_terms_start_date(self) -> Optional[date]:
        """
        Date where BillModel term start to apply.

        Returns
        _______
        date
            A date which represents the start of BillModel terms.
        """
        return self.date_approved

    def _get_next_state_model(self, raise_exception: bool = True):
        """
        Fetches the next sequenced state model associated with the BillModel number.

        Parameters
        ----------
        raise_exception: bool
            Raises IntegrityError if unable to secure transaction from DB.

        Returns
        -------
        EntityStateModel
            An instance of EntityStateModel
        """
        EntityStateModel = lazy_loader.get_entity_state_model()
        EntityModel = lazy_loader.get_entity_model()
        entity_model = EntityModel.objects.get(uuid__exact=self.ledger.entity_id)
        fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

        try:
            LOOKUP = {
                'entity_model_id__exact': self.ledger.entity_id,
                'entity_unit_id__exact': None,
                'fiscal_year': fy_key,
                'key__exact': EntityStateModel.KEY_BILL
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_related(
                'entity_model').select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save(update_fields=['sequence'])
            state_model.refresh_from_db()
            return state_model
        except ObjectDoesNotExist:
            EntityModel = lazy_loader.get_entity_model()
            entity_model = EntityModel.objects.get(uuid__exact=self.ledger.entity_id)
            fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

            LOOKUP = {
                'entity_model_id': entity_model.uuid,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key': EntityStateModel.KEY_BILL,
                'sequence': 1
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_bill_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next BillModel document number available. The operation
        will result in two additional queries if the BillModel & LedgerModel is not cached in
        QuerySet via select_related('ledger').

        Parameters
        __________
        commit: bool
            Commits transaction into BillModel.

        Returns
        _______
        str
            A String, representing the generated BillModel instance Document Number.
        """
        if self.can_generate_bill_number():
            with transaction.atomic(durable=True):

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

                seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
                self.bill_number = f'{DJANGO_LEDGER_BILL_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'

                if commit:
                    self.save(update_fields=['bill_number', 'updated'])

        return self.bill_number

    def generate_descriptive_title(self) -> str:
        return f'Bill {self.bill_number} | {self.get_bill_status_display()} {self.get_status_action_date()} | {self.vendor.vendor_name}'

    # --> URLs <---
    def get_absolute_url(self):
        return reverse('django_ledger:bill-detail',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def clean(self, commit: bool = True):
        """
        Clean method for BillModel. Results in a DB query if bill number has not been generated and the BillModel is
        eligible to generate a bill_number.

        Parameters
        __________

        commit: bool
            If True, commits into DB the generated BillModel number if generated.
        """

        super(AccrualMixIn, self).clean()
        super(PaymentTermsMixIn, self).clean()

        if self.accrue:
            self.progress = Decimal.from_float(1.00)

        if self.is_draft():
            self.amount_paid = Decimal.from_float(0.00)
            self.paid = False
            self.date_paid = None

        if not self.additional_info:
            self.additional_info = dict()


class BillModel(BillModelAbstract):
    """
    Base BillModel from Abstract.
    """


def billmodel_presave(instance: BillModel, **kwargs):
    if instance.can_generate_bill_number():
        instance.generate_bill_number(commit=False)


pre_save.connect(receiver=billmodel_presave, sender=BillModel)


def billmodel_predelete(instance: BillModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=billmodel_predelete, sender=BillModel)
