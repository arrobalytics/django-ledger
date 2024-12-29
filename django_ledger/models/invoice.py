"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

This module implements the InvoiceModel, which represents the Sales Invoice/ Sales Invoice/ Tax Invoice/ Proof of Sale
which the :func:`EntityModel <django_ledger.models.entity.EntityModel>` issues to its customers for the supply of
goods or services. The model manages all the Sales Invoices which are issued by the :func:`EntityModel
<django_ledger.models.entity.EntityModel>`. In addition to tracking the invoice amount , it tracks the receipt and
due amount.

Examples
________
>>> user_model = request.user  # django UserModel
>>> entity_slug = kwargs['entity_slug'] # may come from view kwargs
>>> invoice_model = InvoiceModel()
>>> ledger_model, invoice_model = invoice_model.configure(entity_slug=entity_slug, user_model=user_model)
>>> invoice_model.save()
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Union, Optional, Tuple, Dict
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, F, Count
from django.db.models.signals import pre_save
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.io.io_core import get_localtime, get_localdate
from django_ledger.models import (
    lazy_loader, ItemTransactionModelQuerySet,
    ItemModelQuerySet, ItemModel, QuerySet, Manager
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.mixins import (
    CreateUpdateMixIn, AccrualMixIn,
    MarkdownNotesMixIn, PaymentTermsMixIn,
    ItemizeMixIn
)
from django_ledger.models.signals import (
    invoice_status_draft,
    invoice_status_in_review,
    invoice_status_approved,
    invoice_status_paid,
    invoice_status_canceled,
    invoice_status_void
)
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_INVOICE_NUMBER_PREFIX

UserModel = get_user_model()


class InvoiceModelValidationError(ValidationError):
    pass


class InvoiceModelQuerySet(QuerySet):
    """
   A custom defined QuerySet for the InvoiceModel.
   This implements multiple methods or queries that we need to run to get a status of Invoices raised by the entity.
   For example, We might want to have list of invoices which are paid, unpaid, due , overDue, approved or in draft stage.
   All these separate functions will assist in making such queries and building customized reports.
   """

    def draft(self):
        """
        Default status of any invoice that is created.
        Draft invoices do not impact the Ledger.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of draft invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_DRAFT)

    def in_review(self):
        """
        In review invoices are those that need additional review or approvals before being approved.
        Draft invoices do not impact the Ledger.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of in review invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_DRAFT)

    def approved(self):
        """
        Approved invoices are those that have been reviewed and are expected to be paid before the due date.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of approved invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED)

    def paid(self):
        """
        Paid invoices are those that have received 100% of the amount due.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of paid invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_PAID)

    def void(self):
        """
        Void invoices are those that where rolled back after being approved.
        Void invoices rollback all transactions by creating a new set of transactions posted on the date_void.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of void invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_VOID)

    def canceled(self):
        """
        Canceled invoices are those that are discarded during the draft or in review status.
        These invoices never had an impact on the books.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of canceled invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_CANCELED)

    def active(self):
        """
        Active invoices are those that are approved or paid, which have
        impacted or have the potential to impact the Entity's Ledgers.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of active invoices only.
        """
        return self.filter(
            Q(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED) |
            Q(invoice_status__exact=InvoiceModel.INVOICE_STATUS_PAID)
        )

    def overdue(self):
        """
        Overdue invoices are those which due date is in the past.

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of overdue invoices only.
        """
        return self.filter(date_due__lt=get_localdate())

    def unpaid(self):
        """
        Unpaid invoices are those that are approved but have not received 100% of the amount due.
        Equivalent to approved().

        Returns
        -------
        InvoiceModelQuerySet
            Returns a QuerySet of paid invoices only.
        """
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED)


class InvoiceModelManager(Manager):
    """
    A custom defined InvoiceModel Manager that will act as an interface to handling the DB queries to the InvoiceModel.
    The default "get_queryset" has been overridden to refer the custom defined "InvoiceModelQuerySet"
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'ledger',
            'ledger__entity'
        )

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model) -> InvoiceModelQuerySet:
        """
        Returns a QuerySet of InvoiceModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            The request UserModel to check for privileges.

        Returns
        -------
        InvoiceModelQuerySet
            A Filtered InvoiceModelQuerySet.
        """
        qs = self.for_user(user_model)
        if isinstance(entity_slug, EntityModel):
            return qs.filter(ledger__entity=entity_slug)
        elif isinstance(entity_slug, str):
            return qs.filter(ledger__entity__slug__exact=entity_slug)

    def for_entity_unpaid(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.approved()


class InvoiceModelAbstract(
    AccrualMixIn,
    ItemizeMixIn,
    PaymentTermsMixIn,
    MarkdownNotesMixIn,
    CreateUpdateMixIn
):
    """
    This is the main abstract class which the InvoiceModel database will inherit from.
    The InvoiceModel inherits functionality from the following MixIns:
    
        1. :func:`LedgerWrapperMixIn <django_ledger.models.mixins.LedgerWrapperMixIn>`
        2. :func:`PaymentTermsMixIn <django_ledger.models.mixins.PaymentTermsMixIn>`
        3. :func:`MarkdownNotesMixIn <django_ledger.models.mixins.MarkdownNotesMixIn>`
        4. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`


    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    invoice_number: str
        Auto assigned number at creation by generate_invoice_number() function.
        Prefix be customized with DJANGO_LEDGER_INVOICE_NUMBER_PREFIX setting.
        Includes a reference to the Fiscal Year, Entity Unit and a sequence number. Max Length is 20.
    invoice_status: str
        Current status of the InvoiceModel. Must be one of the choices as mentioned under "INVOICE_STATUS".
        By default, the status will be "Draft".
    customer: :obj:`CustomerModel`
        This is the foreign key reference to the CustomerModel from whom the purchase has been made.
    additional_info: dict
        Any additional metadata about the InvoiceModel may be stored here as a dictionary object.
        The data is serialized and stored as a JSON document in the Database.
    invoice_items:
        A foreign key reference to the list of ItemTransactionModel that make the invoice amount.
    ce_model: EstimateModel
        A foreign key to the InvoiceModel associated EstimateModel for overall Job/Contract tracking.
    date_draft: date
        The draft date represents the date when the InvoiceModel was first created.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_in_review: date
        The in review date represents the date when the InvoiceModel was marked as In Review status.
        Will be null if InvoiceModel is canceled during draft status. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.
    date_approved: date
        The approved date represents the date when the InvoiceModel was approved.
        Will be null if InvoiceModel is canceled.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_paid: date
        The paid date represents the date when the InvoiceModel was paid and amount_due equals amount_paid.
        Will be null if InvoiceModel is canceled. Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_void: date
        The void date represents the date when the InvoiceModel was void, if applicable.
        Will be null unless InvoiceModel is void. Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_canceled: date
        The canceled date represents the date when the InvoiceModel was canceled, if applicable.
        Will be null unless InvoiceModel is canceled. Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    """

    IS_DEBIT_BALANCE = True
    REL_NAME_PREFIX = 'invoice'

    INVOICE_STATUS_DRAFT = 'draft'
    INVOICE_STATUS_REVIEW = 'in_review'
    INVOICE_STATUS_APPROVED = 'approved'
    INVOICE_STATUS_PAID = 'paid'
    INVOICE_STATUS_VOID = 'void'
    INVOICE_STATUS_CANCELED = 'canceled'

    INVOICE_STATUS = [
        (INVOICE_STATUS_DRAFT, _('Draft')),
        (INVOICE_STATUS_REVIEW, _('In Review')),
        (INVOICE_STATUS_APPROVED, _('Approved')),
        (INVOICE_STATUS_PAID, _('Paid')),
        (INVOICE_STATUS_VOID, _('Void')),
        (INVOICE_STATUS_CANCELED, _('Canceled'))
    ]
    """
    The different invoice status options and their representation in the Database.
    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    invoice_number = models.SlugField(max_length=20,
                                      editable=False,
                                      verbose_name=_('Invoice Number'))
    invoice_status = models.CharField(max_length=10, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0],
                                      verbose_name=_('Invoice Status'))
    customer = models.ForeignKey('django_ledger.CustomerModel',
                                 on_delete=models.RESTRICT,
                                 verbose_name=_('Customer'))

    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.RESTRICT,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    prepaid_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.RESTRICT,
                                        verbose_name=_('Prepaid Account'),
                                        related_name=f'{REL_NAME_PREFIX}_prepaid_account')
    unearned_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.RESTRICT,
                                         verbose_name=_('Unearned Account'),
                                         related_name=f'{REL_NAME_PREFIX}_unearned_account')

    additional_info = models.JSONField(blank=True,
                                       null=True,
                                       default=dict,
                                       verbose_name=_('Invoice Additional Info'))
    invoice_items = models.ManyToManyField('django_ledger.ItemModel',
                                           through='django_ledger.ItemTransactionModel',
                                           through_fields=('invoice_model', 'item_model'),
                                           verbose_name=_('Invoice Items'))

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

    objects = InvoiceModelManager.from_queryset(queryset_class=InvoiceModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        indexes = [
            models.Index(fields=['invoice_status']),
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

            models.Index(fields=['customer']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return f'Invoice: {self.invoice_number} | {self.get_invoice_status_display()}'

    def is_configured(self) -> bool:
        return all([
            super().is_configured(),
            self.invoice_status
        ])

    def configure(self,
                  entity_slug: Union[EntityModel, str],
                  user_model: Optional[UserModel] = None,
                  date_draft: Optional[date] = None,
                  ledger_posted: bool = False,
                  ledger_name: Optional[str] = None,
                  commit: bool = False,
                  commit_ledger: bool = False):
        """
        A configuration hook which executes all initial InvoiceModel setup on to the LedgerModel and all initial
        values of the InvoiceModel. Can only call this method once in the lifetime of a InvoiceModel.

        Parameters
        __________

        entity_slug: str or EntityModel
            The entity slug or EntityModel to associate the Invoice with.
        user_model: UserModel
            The UserModel making the request to check for QuerySet permissions.
        ledger_posted: bool
            An option to mark the InvoiceModel Ledger as posted at the time of configuration. Defaults to False.
        ledger_name: str
            Optional additional InvoiceModel ledger name or description.
        invoice_desc: str
            An optional description appended to the LedgerModel name.
        commit: bool
            Saves the current InvoiceModel after being configured.
        commit_ledger: bool
            Saves the InvoiceModel's LedgerModel while being configured.
        Returns
        -------
        A tuple of LedgerModel, InvoiceModel
        """

        if not self.is_configured():
            if isinstance(entity_slug, str):
                if not user_model:
                    raise InvoiceModelValidationError(_('Must pass user_model when using entity_slug.'))
                entity_qs = EntityModel.objects.for_user(user_model=user_model)
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
            elif isinstance(entity_slug, EntityModel):
                entity_model = entity_slug
            else:
                raise InvoiceModelValidationError('entity_slug must be an instance of str or EntityModel')

            if entity_model.is_accrual_method():
                self.accrue = True
                self.progress = Decimal.from_float(1.00)
            else:
                self.accrue = False

            self.invoice_status = self.INVOICE_STATUS_DRAFT
            self.date_draft = get_localdate() if not date_draft else date_draft

            LedgerModel = lazy_loader.get_ledger_model()
            ledger_model: LedgerModel = LedgerModel(entity=entity_model, posted=ledger_posted)
            ledger_model.configure_for_wrapper_model(model_instance=self)
            ledger_name = f'Invoice {self.uuid}' if not ledger_name else ledger_name
            ledger_model.name = ledger_name
            ledger_model.clean()
            ledger_model.clean_fields()
            self.ledger = ledger_model

            if commit_ledger or commit:
                self.ledger.save()

            if self.can_generate_invoice_number():
                self.generate_invoice_number(commit=commit)
                ledger_model.ledger_xid = f'invoice-{self.invoice_number.lower()}-{str(ledger_model.entity_id)[-5:]}'
                ledger_model.save(update_fields=['ledger_xid'])

            self.clean()

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
        ).invoices()

    def validate_itemtxs_qs(self, queryset: ItemTransactionModelQuerySet):
        """
        Validates that the entire ItemTransactionModelQuerySet is bound to the InvoiceModel.

        Parameters
        ----------
        queryset: ItemTransactionModelQuerySet
            ItemTransactionModelQuerySet to validate.
        """
        valid = all([
            i.invoice_model_id == self.uuid for i in queryset
        ])
        if not valid:
            raise InvoiceModelValidationError(f'Invalid queryset. All items must be assigned to Invoice {self.uuid}')

    def get_itemtxs_data(self,
                         queryset: ItemTransactionModelQuerySet = None,
                         aggregate_on_db: bool = False,
                         lazy_agg: bool = False,
                         ) -> Tuple[ItemTransactionModelQuerySet, Dict]:
        """
        Fetches the InvoiceModel Items and aggregates the QuerySet.

        Parameters
        __________
        queryset:
            Optional pre-fetched ItemModelQueryset to use. Avoids additional DB query if provided.

        Returns
        _______
        A tuple: ItemTransactionModelQuerySet, dict
        """

        if not queryset:
            queryset = self.itemtransactionmodel_set.all().select_related(
                'item_model',
                'entity_unit',
                'po_model',
                'invoice_model'
            )
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

    def get_migrate_state_desc(self):
        """
        Description used when migrating transactions into the LedgerModel.

        Returns
        _______
        str
            Description as a string.
        """
        return f'Invoice {self.invoice_number} account adjustment.'

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

        return queryset.select_related('item_model').order_by(
            'item_model__earnings_account__uuid',
            'entity_unit__uuid',
            'item_model__earnings_account__balance_type').values(
            'item_model__earnings_account__uuid',
            'item_model__earnings_account__balance_type',
            'item_model__cogs_account__uuid',
            'item_model__cogs_account__balance_type',
            'item_model__inventory_account__uuid',
            'item_model__inventory_account__balance_type',
            'item_model__inventory_received',
            'item_model__inventory_received_value',
            'entity_unit__slug',
            'entity_unit__uuid',
            'quantity',
            'total_amount').annotate(
            account_unit_total=Sum('total_amount'))

    def update_amount_due(self,
                          itemtxs_qs: Optional[ItemTransactionModelQuerySet] = None) -> ItemTransactionModelQuerySet:
        """
        Updates the InvoiceModel amount due.

        Parameters
        ----------
        itemtxs_qs: ItemTransactionModelQuerySet
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

    # STATE...
    def is_draft(self) -> bool:
        """
        Checks if the InvoiceModel is in Draft status.

        Returns
        _______
        bool
            True if InvoiceModel is Draft, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_DRAFT

    def is_review(self) -> bool:
        """
        Checks if the InvoiceModel is In Review status.

        Returns
        _______
        bool
            True if InvoiceModel is in Review, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_REVIEW

    def is_approved(self) -> bool:
        """
        Checks if the InvoiceModel is in Approved status.

        Returns
        _______
        bool
            True if InvoiceModel is Approved, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_APPROVED

    def is_paid(self) -> bool:
        """
        Checks if the InvoiceModel is in Paid status.

        Returns
        _______
        bool
            True if InvoiceModel is Paid, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_PAID

    def is_active(self):
        """
        Checks if the InvoiceModel has the potential to impact the books and produce financial statements status.

        Returns
        _______
        bool
            True if InvoiceModel is Active, else False.
        """
        return any([
            self.is_paid(),
            self.is_approved(),
            self.is_void()
        ])

    def is_canceled(self) -> bool:
        """
        Checks if the InvoiceModel is in Canceled status.

        Returns
        _______
        bool
            True if InvoiceModel is Canceled, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_CANCELED

    def is_void(self) -> bool:
        """
        Checks if the InvoiceModel is in Void status.

        Returns
        _______
        bool
            True if InvoiceModel is Void, else False.
        """
        return self.invoice_status == self.INVOICE_STATUS_VOID

    def is_past_due(self) -> bool:
        """
        Checks if the InvoiceModel is past due.

        Returns
        -------
        bool
            True if InvoiceModel is past due, else False.
        """
        if self.date_due and self.is_approved():
            return self.date_due < get_localdate()
        return False

    # PERMISSIONS....
    def can_draft(self):
        """
        Checks if the InvoiceModel can be marked as Draft.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as draft, else False.
        """
        return self.is_review()

    def can_review(self):
        """
        Checks if the InvoiceModel can be marked as In Review.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as in review, else False.
        """
        return all([
            self.is_configured(),
            self.is_draft()
        ])

    def can_approve(self):
        """
        Checks if the InvoiceModel can be marked as Approved.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as approved, else False.
        """
        return self.is_review()

    def can_pay(self):
        """
        Checks if the InvoiceModel can be marked as Paid.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as paid, else False.
        """
        return self.is_approved()

    def can_delete(self):
        """
        Checks if the InvoiceModel can be deleted.

        Returns
        -------
        bool
            True if InvoiceModel can be deleted, else False.
        """
        return any([
            self.is_review(),
            self.is_draft(),
            not self.ledger.is_locked()
        ])

    def can_void(self):
        """
        Checks if the InvoiceModel can be marked as Void status.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as void, else False.
        """
        return all([
            self.is_approved(),
            float(self.amount_paid) == 0.00
        ])

    def can_cancel(self):
        """
        Checks if the InvoiceModel can be marked as Canceled status.

        Returns
        -------
        bool
            True if InvoiceModel can be marked as canceled, else False.
        """
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self):
        """
        Checks if the InvoiceModel item transactions can be edited.

        Returns
        -------
        bool
            True if InvoiceModel items can be edited, else False.
        """
        return self.is_draft()

    def can_migrate(self):
        """
        Checks if the InvoiceModel can be migrated.

        Returns
        -------
        bool
            True if InvoiceModel can be migrated, else False.
        """
        can_migrate = super().can_migrate()
        if not can_migrate:
            return False
        return self.is_approved()

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        """
        Checks if the InvoiceModel can be bound to a given EstimateModel.

        Parameters
        __________

        estimate_model: EstimateModel
            EstimateModel to check against.

        raise_exception: bool
            If True, raises InvoiceModelValidationError if unable to bind. Else, returns False.

        Returns
        _______

        bool
            True if can bind provided EstimateModel, else False.
        """

        if self.ce_model_id:
            if raise_exception:
                raise InvoiceModelValidationError(f'Invoice {self.invoice_number} already bound to '
                                                  f'Estimate {self.ce_model.estimate_number}')
            return False

        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise InvoiceModelValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    def can_generate_invoice_number(self):
        """
        Checks if InvoiceModel can generate its Document Number.

        Returns
        _______

        bool
            True if InvoiceModel can generate its invoice_number, else False.
        """
        return all([
            self.date_draft,
            not self.invoice_number,
            self.is_configured()
        ])

    # ACTIONS...

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
        Makes a payment to the InvoiceModel.

        Parameters
        __________

        payment_amount: Decimal ot float
            The payment amount to process.

        payment_date: datetime or date.
            Date or timestamp of the payment being applied.

        commit: bool
            If True, commits the transaction into the DB. Defaults to False.

        raise_exception: bool
            If True, raises InvoiceModelValidationError if payment exceeds amount due, else False.

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
                raise InvoiceModelValidationError(
                    f'Amount paid: {self.amount_paid} exceed amount due: {self.amount_due}.'
                )
            return

        self.get_state(commit=True)
        self.clean()

        if not payment_date:
            payment_date = get_localtime()

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

    def bind_estimate(self, estimate_model, commit: bool = False):
        """
        Binds InvoiceModel to a given EstimateModel. Raises ValueError if EstimateModel cannot be bound.

        Parameters
        __________
        estimate_model: EstimateModel
            EstimateModel to bind.

        raise_exception: bool
            Raises InvoiceModelValidationError if unable to bind EstimateModel.

        commit: bool
            Commits transaction into current InvoiceModel.
        """

        try:
            self.can_bind_estimate(estimate_model, raise_exception=True)
        except ValueError as e:
            raise e

        self.ce_model = estimate_model
        self.customer_id = estimate_model.customer_id
        self.clean()
        if commit:
            self.save(update_fields=[
                'ce_model',
                'customer_id',
                'updated'
            ])

    # DRAFT...
    def mark_as_draft(self, draft_date: Union[date, datetime], commit: bool = False, **kwargs):
        """
        Marks InvoiceModel as Draft.

        Parameters
        __________

        date_draft: date
            Draft date. If None, defaults to localdate().

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_draft():
            raise InvoiceModelValidationError(f'Cannot mark PO {self.uuid} as draft...')

        if draft_date:
            if isinstance(draft_date, datetime):
                self.draft_date = draft_date.date()
            elif isinstance(draft_date, date):
                self.draft_date = draft_date
        else:
            self.draft_date = get_localdate()

        self.invoice_status = self.INVOICE_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
                'updated'
            ])
        invoice_status_draft.send_robust(sender=self.__class__,
                                         instance=self,
                                         commited=commit, **kwargs)

    def get_mark_as_draft_html_id(self):
        """
        InvoiceModel Mark as Draft HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String
        """
        return f'djl-{self.uuid}-invoice-mark-as-draft'

    def get_mark_as_draft_url(self):
        """
        InvoiceModel Mark-as-Draft action URL.

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
        return reverse('django_ledger:invoice-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Draft InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as Draft?') % self.invoice_number

    # REVIEW...
    def mark_as_review(self,
                       date_in_review: date = None,
                       itemtxs_qs=None,
                       commit: bool = False,
                       **kwargs):
        """
        Marks InvoiceModel as In Review.

        Parameters
        __________

        date_in_review: date
            InvoiceModel in review date. Defaults to localdate() if None.
        itemtxs_qs: ItemTransactionModelQuerySet
            Pre fetched ItemTransactionModelQuerySet to use. Avoids additional DB Query if previously fetched.
        commit: bool
            Commits transaction into the Database. Defaults to False.
        raise_exception: bool
            Raises InvoiceModelValidationError if InvoiceModel cannot be marked as in review. Defaults to True.
        """
        if not self.can_review():
            raise InvoiceModelValidationError(f'Cannot mark PO {self.uuid} as In Review...')

        self.date_in_review = get_localdate() if not date_in_review else date_in_review

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()
        if not itemtxs_qs.count():
            raise InvoiceModelValidationError(message='Cannot review an Invoice without items...')
        if not self.amount_due:
            raise InvoiceModelValidationError(
                f'PO {self.invoice_number} cannot be marked as in review. Amount due must be greater than 0.'
            )

        self.invoice_status = self.INVOICE_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
                'date_in_review',
                'updated'
            ])
        invoice_status_in_review.send_robust(sender=self.__class__,
                                             instance=self,
                                             commited=commit,
                                             **kwargs)

    def get_mark_as_review_html_id(self):
        """
        InvoiceModel Mark as In Review HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-invoice-mark-as-review'

    def get_mark_as_review_url(self):
        """
        InvoiceModel Mark-as-Review action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            InvoiceModel mark-as-review action URL.
        """
        return reverse('django_ledger:invoice-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Review InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as In Review?') % self.invoice_number

    # APPROVED...
    def mark_as_approved(self,
                         entity_slug,
                         user_model,
                         date_approved: date = None,
                         commit: bool = False,
                         force_migrate: bool = False,
                         raise_exception: bool = True,
                         **kwargs):
        """
        Marks InvoiceModel as Approved.

        Parameters
        __________

        entity_slug
            Entity slug associated with the InvoiceModel. Avoids additional DB query if passed.

        user_model
            UserModel associated with request.

        date_approved: date
            InvoiceModel approved date. Defaults to localdate().

        commit: bool
            Commits transaction into the Database. Defaults to False.

        force_migrate: bool
            Forces migration. True if Accounting Method is Accrual.
        """
        if not self.can_approve():
            if raise_exception:
                raise InvoiceModelValidationError(f'Cannot mark PO {self.uuid} as Approved...')
            return

        self.invoice_status = self.INVOICE_STATUS_APPROVED

        if date_approved:
            if isinstance(date_approved, datetime):
                self.date_approved = date_approved.date()
            elif isinstance(date_approved, date):
                self.draft_date = date_approved
        else:
            self.date_approved = get_localdate()

        self.clean()
        if commit:
            self.save()
            if force_migrate or self.accrue:
                # normally no transactions will be present when marked as approved...
                self.migrate_state(
                    entity_slug=entity_slug,
                    user_model=user_model,
                    je_timestamp=date_approved,
                    force_migrate=self.accrue
                )
            self.ledger.post(commit=commit, raise_exception=raise_exception)
        invoice_status_approved.send_robust(sender=self.__class__,
                                            instance=self,
                                            commited=commit,
                                            **kwargs)

    def get_mark_as_approved_html_id(self):
        """
        InvoiceModel Mark as Approved HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-invoice-mark-as-approved'

    def get_mark_as_approved_url(self):
        """
        InvoiceModel Mark-as-Approved action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            InvoiceModel mark-as-approved action URL.
        """
        return reverse('django_ledger:invoice-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Approved InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as Approved?') % self.invoice_number

    # PAID...
    def mark_as_paid(self,
                     entity_slug: str,
                     user_model,
                     date_paid: date = None,
                     commit: bool = False,
                     **kwargs):
        """
        Marks InvoiceModel as Paid.

        Parameters
        __________

        entity_slug: str
            Entity slug associated with the InvoiceModel. Avoids additional DB query if passed.

        user_model:
            UserModel associated with request.

        date_paid: date
            InvoiceModel paid date. Defaults to localdate() if None.

        itemtxs_qs: ItemTransactionModelQuerySet
            Pre-fetched ItemTransactionModelQuerySet. Avoids additional DB query. Validated if passed.

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """

        if not self.can_pay():
            raise InvoiceModelValidationError(f'Cannot mark PO {self.uuid} as Paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due

        if date_paid:
            if isinstance(date_paid, datetime):
                self.date_paid = date_paid.date()
            elif isinstance(date_paid, date):
                self.date_paid = date_paid
        else:
            self.date_paid = get_localdate()

        if self.date_paid > get_localdate():
            raise InvoiceModelValidationError(f'Cannot pay {self.__class__.__name__} in the future.')

        self.get_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_PAID
        self.clean()

        if commit:
            self.save()
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                force_migrate=True,
                je_timestamp=date_paid
            )
            self.lock_ledger(commit=True)
        invoice_status_paid.send_robust(sender=self.__class__,
                                        instance=self,
                                        commited=commit,
                                        **kwargs)

    def get_mark_as_paid_html_id(self):
        """
        InvoiceModel Mark as Paid HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String
        """
        return f'djl-{self.uuid}-invoice-mark-as-paid'

    def get_mark_as_paid_url(self, entity_slug: str = None):
        """
        InvoiceModel Mark-as-Paid action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            InvoiceModel mark-as-paid action URL.
        """
        if not entity_slug:
            entity_slug = self.ledger.entity.slug
        return reverse('django_ledger:invoice-action-mark-as-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_paid_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Paid InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as Paid?') % self.invoice_number

    # VOID...
    def mark_as_void(self,
                     entity_slug: str,
                     user_model,
                     date_void: Optional[Union[date, datetime]] = None,
                     commit: bool = False,
                     **kwargs):
        """
        Marks InvoiceModel as Void.
        When mark as void, all transactions associated with InvoiceModel are reversed as of the void date.

        Parameters
        __________

        entity_slug: str
            Entity slug associated with the InvoiceModel. Avoids additional DB query if passed.

        user_model
            UserModel associated with request.

        date_void: date
            InvoiceModel void date. Defaults to localdate() if None.

        commit: bool
            Commits transaction into DB. Defaults to False.
        """
        if not self.can_void():
            raise InvoiceModelValidationError(f'Cannot mark Invoice {self.uuid} as Void...')

        if date_void:
            if isinstance(date_void, datetime):
                self.date_void = date_void.date()
            elif isinstance(date_void, date):
                self.date_void = date_void
        else:
            self.date_void = get_localdate()

        if self.date_void > get_localdate():
            raise InvoiceModelValidationError(f'Cannot void {self.__class__.__name__} in the future.')
        if self.date_void < self.date_approved:
            raise InvoiceModelValidationError(
                f'Cannot void {self.__class__.__name__} at {self.date_void} before approved '
                f'{self.date_approved}')

        self.void_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_VOID
        self.clean()

        if commit:
            self.unlock_ledger(commit=True, raise_exception=False)
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                void=True,
                void_date=self.date_void,
                force_migrate=True,
                raise_exception=False
            )
            self.save()
            self.lock_ledger(commit=True, raise_exception=False)
        invoice_status_void.send_robust(sender=self.__class__,
                                        instance=self,
                                        commited=commit,
                                        **kwargs)

    def get_mark_as_void_html_id(self):
        """
        InvoiceModel Mark as Void HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-invoice-mark-as-void'

    def get_mark_as_void_url(self):
        """
        InvoiceModel Mark-as-Void action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
            InvoiceModel mark-as-void action URL.
        """
        return reverse('django_ledger:invoice-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Void InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as Void?') % self.invoice_number

    # CANCEL
    def mark_as_canceled(self,
                         date_canceled: date = None,
                         commit: bool = False,
                         **kwargs):
        """
        Mark InvoiceModel as Canceled.

        Parameters
        __________

        date_canceled: date
            InvoiceModel canceled date. Defaults to localdate() if None.

        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_cancel():
            raise InvoiceModelValidationError(f'Cannot cancel Invoice {self.invoice_number}.')

        self.date_canceled = get_localdate() if not date_canceled else date_canceled
        self.invoice_status = self.INVOICE_STATUS_CANCELED
        self.clean()
        if commit:
            self.unlock_ledger(commit=True, raise_exception=False)
            self.unpost_ledger(commit=True, raise_exception=False)
            self.save()
        invoice_status_canceled.send_robust(sender=self.__class__,
                                            instance=self,
                                            commited=commit,
                                            **kwargs)

    def get_mark_as_canceled_html_id(self):
        """
        InvoiceModel Mark as Canceled HTML ID Tag.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-invoice-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        """
        InvoiceModel Mark-as-Canceled action URL.

        Parameters
        __________
        entity_slug: str
            Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
            is not cached on QuerySet.

        Returns
        _______
        str
            InvoiceModel mark-as-canceled action URL.
        """
        return reverse('django_ledger:invoice-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        """
        Internationalized confirmation message with Invoice Number.

        Returns
        _______
        str
            Mark-as-Canceled InvoiceModel confirmation message as a String.
        """
        return _('Do you want to mark Invoice %s as Canceled?') % self.invoice_number

    # DELETE ACTIONS...
    def delete(self, force_db_delete: bool = False, using=None, keep_parents=False):
        if not force_db_delete:
            self.mark_as_canceled(commit=True)
            return
        if not self.can_delete():
            raise InvoiceModelValidationError(
                message=_(f'Invoice {self.invoice_number} cannot be deleted...')
            )
        return super().delete(using=using, keep_parents=keep_parents)

    # def mark_as_delete(self, **kwargs):
    #     """
    #     Deletes InvoiceModel from DB if possible. Raises exception if can_delete() is False.
    #     """
    #     if not self.can_delete():
    #         raise InvoiceModelValidationError(
    #             f'Invoice {self.invoice_number} cannot be deleted. Must be void after Approved.')
    #     self.delete(**kwargs)
    #
    # # def get_mark_as_delete_html_id(self) -> str:
    #     """
    #     InvoiceModel Mark as Delete URL.
    #
    #     Returns
    #     _______
    #
    #     str
    #         URL as a String.
    #     """
    #     return f'djl-invoice-model-{self.uuid}-mark-as-delete'
    #
    # def get_mark_as_delete_url(self, entity_slug: Optional[str] = None) -> str:
    #     """
    #     InvoiceModel Mark-as-Delete action URL.
    #
    #     Parameters
    #     __________
    #     entity_slug: str
    #         Entity Slug kwarg. If not provided, will result in addition DB query if select_related('ledger__entity')
    #         is not cached on QuerySet.
    #
    #     Returns
    #     _______
    #     str
    #         InvoiceModel mark-as-delete action URL.
    #     """
    #     if not entity_slug:
    #         entity_slug = self.ledger.entity.slug
    #     return reverse('django_ledger:invoice-action-mark-as-delete',
    #                    kwargs={
    #                        'entity_slug': entity_slug,
    #                        'invoice_pk': self.uuid
    #                    })
    #
    # def get_mark_as_delete_message(self) -> str:
    #     """
    #     Internationalized confirmation message with Invoice Number.
    #
    #     Returns
    #     _______
    #     str
    #         Mark-as-Delete InvoiceModel confirmation message as a String.
    #     """
    #     return _('Do you want to delete Invoice %s?') % self.invoice_number

    # ACTIONS END....
    def get_status_action_date(self):
        """
        Current status action date.

        Returns
        _______
        date
            A date. i.e. If status is Approved, return date_approved. If Paid, return date_paid.
        """
        return getattr(self, f'date_{self.invoice_status}')

    def get_document_id(self):
        """
        Human-readable document number. Defaults to invoice_number.

        Returns
        _______
        str
            Document Number as a String.
        """
        return self.invoice_number

    def get_html_id(self):
        """
        Unique InvoiceNumber HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-invoice-model-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_html_amount_due_id(self):
        """
        Unique amount due HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-invoice-model-{self.REL_NAME_PREFIX}-{self.uuid}-amount-due'

    def get_html_amount_paid_id(self):
        """
        Unique amount paid HTML ID

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-invoice-model-{self.REL_NAME_PREFIX}-{self.uuid}-amount-paid'

    def get_html_form_id(self):
        """
        Unique InvoiceModel Form HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-invoice-model-{self.REL_NAME_PREFIX}-{self.uuid}-form'

    def get_terms_start_date(self) -> date:
        """
        Date where InvoiceModel term start to apply.

        Returns
        _______
        date
            A date which represents the start of InvoiceModel terms.
        """
        return self.date_approved

    def _get_next_state_model(self, raise_exception=True):
        """
        Fetches the next sequenced state model associated with the InvoiceModel number.

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
                'key__exact': EntityStateModel.KEY_INVOICE
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_related(
                'entity_model').select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
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
                'key': EntityStateModel.KEY_INVOICE,
                'sequence': 1
            }

            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_invoice_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next InvoiceModel document number available. The operation
        will result in two additional queries if the InvoiceModel & LedgerModel is not cached in
        QuerySet via select_related('ledger').

        Parameters
        __________
        commit: bool
            Commits transaction into InvoiceModel.

        Returns
        _______
        str
            A String, representing the generated InvoiceModel instance Document Number.
        """
        if self.can_generate_invoice_number():
            with transaction.atomic(durable=True):
                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)
                seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
                self.invoice_number = f'{DJANGO_LEDGER_INVOICE_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'

                if commit:
                    self.save(update_fields=['invoice_number'])
        return self.invoice_number

    def generate_descriptive_title(self) -> str:
        return f'Bill {self.invoice_number} | {self.get_invoice_status_display()} {self.get_status_action_date()} | {self.customer.customer_name}'

    # --> URLs <---
    def get_absolute_url(self):
        return reverse('django_ledger:invoice-detail',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def clean(self, commit: bool = True):
        """
        Clean method for InvoiceModel. Results in a DB query if invoice number has not been generated and the
        InvoiceModel is eligible to generate an invoice_number.

        Parameters
        __________

        commit: bool
            If True, commits into DB the generated InvoiceModel number if generated.
        """

        super().clean()

        if self.cash_account.role != ASSET_CA_CASH:
            raise ValidationError(f'Cash account must be of role {ASSET_CA_CASH}.')
        if self.prepaid_account.role != ASSET_CA_RECEIVABLES:
            raise ValidationError(f'Prepaid account must be of role {ASSET_CA_RECEIVABLES}.')
        if self.unearned_account.role != LIABILITY_CL_DEFERRED_REVENUE:
            raise ValidationError(f'Unearned account must be of role {LIABILITY_CL_DEFERRED_REVENUE}.')

    def save(self, **kwargs):
        """
        Save method for InvoiceModel. Results in a DB query if invoice number has not been generated and the
        InvoiceModel is eligible to generate a invoice_number.
        """
        if self.can_generate_invoice_number():
            self.generate_invoice_number(commit=True)
        super(InvoiceModelAbstract, self).save(**kwargs)


class InvoiceModel(InvoiceModelAbstract):
    """
    Base Invoice Model from Abstract.
    """

    class Meta(InvoiceModelAbstract.Meta):
        swappable = 'DJANGO_LEDGER_INVOICE_MODEL'
        abstract = False


def invoicemodel_presave(instance: InvoiceModel, **kwargs):
    if instance.can_generate_invoice_number():
        instance.generate_invoice_number(commit=False)


pre_save.connect(receiver=invoicemodel_presave, sender=InvoiceModel)
