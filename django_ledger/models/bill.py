"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <ptulshyan77@gmail.com>
"""
from datetime import date
from decimal import Decimal
from string import ascii_uppercase, digits
from typing import Union, Optional
from uuid import uuid4

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, Count, Case, When, Value, ExpressionWrapper, IntegerField, F
from django.db.models.signals import post_delete
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModelQuerySet
from django_ledger.models.mixins import CreateUpdateMixIn, LedgerWrapperMixIn, MarkdownNotesMixIn, PaymentTermsMixIn
from django_ledger.models.utils import LazyLoader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_BILL_NUMBER_PREFIX

lazy_loader = LazyLoader()

BILL_NUMBER_CHARS = ascii_uppercase + digits

"""
Bill : it refers the purchase Invoice/ Tax Invoice/ Purchase Bill which is issued by the Suppliers/ Vendors for the purposes of suppling of goods or services.
The model manages all the Purchase Invoice/ Bills for the purhases mde by the entity.
In addition to tracking the bill amount, it tracks the paid and due amount.


"""


class BillModelQuerySet(models.QuerySet):
    """
    A custom defined Query Set for the BillModel.
    This implements multiple methods or queries that we need to run to get a status of bills.
    For e.g : We might want to have list of bills which are paid, unpaid, due , overdue, approved 
    or in draft stage. All these separate functions will assist in making such queries and building
    customized reports.
    """

    def paid(self):
        """
        Returns a QuerySet of paid bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_PAID)

    def approved(self):
        """
        Returns a QuerySet of approved bills only.
        """
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_APPROVED)

    def active(self):
        """
        Returns a QuerySet of active bills only.
        Active bills are bills that are Approved or Paid.
        """
        return self.filter(
            Q(bill_status__exact=BillModel.BILL_STATUS_APPROVED) |
            Q(bill_status__exact=BillModel.BILL_STATUS_PAID)
        )


class BillModelManager(models.Manager):
    """
    A custom defined BillModel Manager that will act as an interface to handling the DB queries
    to the Bill Model. The default "get_queryset" has been overridden to refer the custom defined
    "BillModelQuerySet"
    """

    def for_user(self, user_model) -> BillModelQuerySet:
        """
        Returns a QuerySet of BillModels that the UserModel as access to.
        User must be a Manager or an Admin to retrieve the BillModels.
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model) -> BillModelQuerySet:
        """
        Returns a QuerySet of BillModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.
        @param entity_slug: The entity slug or EntityModel used for filtering the QuerySet.
        @param user_model: The request UserModel to check for privileges.
        @return: A filtered BillModelQuerySet.
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

    def for_entity_unpaid(self, entity_slug, user_model) -> BillModelQuerySet:
        """
        Returns a QuerySet of unpaid BillModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.
        @param entity_slug: The entity slug or EntityModel used for filtering the QuerySet.
        @param user_model: The request UserModel to check for privileges.
        @return: A filtered BillModelQuerySet.
        """
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.approved()


class BillModelAbstract(LedgerWrapperMixIn,
                        PaymentTermsMixIn,
                        MarkdownNotesMixIn,
                        CreateUpdateMixIn):
    """
    This is the main abstract class which the BillModel database will inherit, and it contains the
    fields/columns/attributes which the said table will have. In addition to the attributes mentioned below,
    it also has the fields/columns/attributes mentioned in below MixIn:
    
    LedgerWrapperMixIn
    PaymentTermsMixIn
    MarkdownNotesMixIn
    CreateUpdateMixIn
    
    Read about these mixin here.

    Below are the fields specific to the BillModel:
    @uuid : this is a unique primary key generated for the table. The default value of this fields is uuid4().
    @bill_number: Auto assigned number at creation. Can be customized with DJANGO_LEDGER_BILL_NUMBER_PREFIX
    settings. Includes a reference to the Fiscal Year, Entity Unit and a sequence number. Max Length is 20.
    @bill_status: Any bill can have the status as either of the choices as mentioned under "BILL_STATUS".
    By default , the status will be "Draft". Options are: Draft, In Review, Approved, Paid, Void or Canceled.
    @xref: This is the filed for capturing of any External reference number like the PO number of the buyer.
    Any other reference number like the Vendor code in buyer books may also be captured.
    @vendor: This is the foreign key reference to the VendorModel from whom the purchase has been made.
    @additional_info: Any additional info about the BillModel may be stored here.
    @bill_items: A foreign key reference to the list of ItemModels that make the bill amount.
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
        ]

    def __str__(self):
        return f'Bill: {self.bill_number}'

    # Configuration...
    def configure(self,
                  entity_slug: Union[str, EntityModel],
                  user_model,
                  ledger_posted: bool = False,
                  bill_desc: str = None,
                  commit: bool = False):
        """
        A configuration hook which executes all initial BillModel setup on to the LedgerModel and all initial
        values of the BillModel. Can only call this method once in the lifetime of a BillModel.

        @param entity_slug: The entity slug or EntityModel to associate the Bill with.
        @param user_model: The UserModel making the request to check for QuerySet permissions.
        @param ledger_posted: An option to mark the BillModel Ledger as posted at the time of configuration. Defaults to False.
        @param bill_desc: An optional description added to the LedgerModel.
        @param commit: Saves the current BillModel at the time
        @return: A tuple of LedgerModel, BillModel
        """

        # todo: add is_configured() check.
        # todo: add raise_exception flag.

        if not self.ledger_id:
            if isinstance(entity_slug, str):
                entity_qs = EntityModel.objects.for_user(
                    user_model=user_model)
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
            elif isinstance(entity_slug, EntityModel):
                entity_model = entity_slug
            else:
                raise ValidationError('entity_slug must be an instance of str or EntityModel')

        if entity_model.is_accrual_method():
            self.accrue = True
            self.progress = 1
        else:
            self.accrue = False

        ledger_name = f'Bill {self.bill_number}'
        if bill_desc:
            ledger_name += f' | {bill_desc}'

        LedgerModel = lazy_loader.get_ledger_model()
        ledger_model: LedgerModel = LedgerModel.objects.create(
            entity=entity_model,
            posted=ledger_posted,
            name=ledger_name,
        )
        ledger_model.clean()
        self.ledger = ledger_model
        self.clean()
        if commit:
            self.save()

        return self.ledger, self

    # State..
    def get_migrate_state_desc(self) -> str:
        """
        Description used when migrating transactions into the LedgerModel.
        @return: Description as a string.
        """
        return f'Bill {self.bill_number} account adjustment.'

    def get_itemtxs_data(self, queryset: ItemTransactionModelQuerySet = None) -> tuple:
        """
        Fetches the BillModel Items and aggregates the QuerySet.
        @param queryset: Optional pre-fetched ItemModelQueryset to use. Avoids additional DB query.
        @return: A tuple. ItemModelQuerySet, Aggregated QuerySet
        """
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.select_related('item_model', 'po_model', 'bill_model').all()
        return queryset, queryset.aggregate(
            Sum('total_amount'),
            total_items=Count('uuid')
        )

    def get_item_data(self, entity_slug, queryset: ItemTransactionModelQuerySet = None):
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.all()
            # queryset = queryset.filter(bill_model__ledger__entity__slug__exact=entity_slug)
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

    def update_amount_due(self, itemtxs_qs=None, itemtxs_list: list = None) -> None or tuple:
        if itemtxs_list:
            # self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            self.amount_due = round(sum(a.total_amount for a in itemtxs_list), 2)
            return
        itemtxs_qs, itemtxs_agg = self.get_itemtxs_data(queryset=itemtxs_qs)
        self.amount_due = round(itemtxs_agg['total_amount__sum'], 2)
        return itemtxs_qs, itemtxs_agg

    # State
    def is_draft(self) -> bool:
        """
        Checks if the BillModel is in Draft status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_DRAFT

    def is_review(self) -> bool:
        """
        Checks if the BillModel is In Review status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_REVIEW

    def is_approved(self) -> bool:
        """
        Checks if the BillModel is in Approved status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_APPROVED

    def is_paid(self) -> bool:
        """
        Checks if the BillModel is in Paid status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_PAID

    def is_canceled(self) -> bool:
        """
        Checks if the BillModel is in Canceled status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_CANCELED

    def is_void(self) -> bool:
        """
        Checks if the BillModel is in Void status.
        @return: True/False as Boolean.
        """
        return self.bill_status == self.BILL_STATUS_VOID

    def is_past_due(self) -> bool:
        if self.date_due and self.is_approved():
            return self.date_due < localdate()
        return False
    # Permissions....
    def can_draft(self) -> bool:
        """
        Checks if the BillModel can be marked as Draft.
        @return: True/False as Boolean.
        """
        return self.is_review()

    def can_review(self) -> bool:
        """
        Checks if the BillModel can be marked as In Review.
        @return: True/False as Boolean.
        """
        return all([
            self.is_configured(),
            self.is_draft()
        ])

    def can_approve(self) -> bool:
        """
        Checks if the BillModel can be marked as Approved.
        @return: True/False as Boolean.
        """
        return self.is_review()

    def can_pay(self) -> bool:
        """
        Checks if the BillModel can be marked as Paid.
        @return: True/False as Boolean.
        """
        return self.is_approved()

    def can_delete(self) -> bool:
        """
        Checks if the BillModel can be deleted.
        @return: True/False as Boolean.
        """
        return any([
            self.is_review(),
            self.is_draft()
        ])

    def can_void(self) -> bool:
        """
        Checks if the BillModel can be marked as Void status.
        @return:
        """
        return self.is_approved()

    def can_cancel(self) -> bool:
        """
        Checks if the BillModel can be marked as Canceled status.
        @return: True/False as Boolean.
        """
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self) -> bool:
        """
        Checks if the BillModel item transactions can be edited.
        @return: True/False as Boolean.
        """
        return self.is_draft()

    def can_migrate(self) -> bool:
        """
        Checks if the BillModel can be migrated.
        @return: True/False as Boolean.
        """
        if not self.is_approved():
            return False
        return super(BillModelAbstract, self).can_migrate()

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        """
        Checks if the BillModel can be bound to a given EstimateModel.
        @param estimate_model: EstimateModel to check against.
        @param raise_exception: If True, raises ValidationError if unable to bind. Else, returns False.
        @return: True/False as Boolean.
        """
        if self.ce_model_id:
            if raise_exception:
                raise ValidationError(f'Bill {self.bill_number} already bound to '
                                      f'Estimate {self.ce_model.estimate_number}')
            return False
        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise ValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    def can_bind_po(self, po_model, raise_exception: bool = False) -> bool:
        """
        Checks if the BillModel can be bound to a given PurchaseOrderModel.
        @param po_model: The PurchaseOrderModel to check against.
        @param raise_exception: If True, raises ValidationError if unable to bind. Else, returns False.
        @return: True/False as Boolean.
        """
        if not po_model.is_approved():
            if raise_exception:
                raise ValidationError(f'Cannot bind an unapproved PO.')
            return False

        if po_model.date_approved > self.date_draft:
            if raise_exception:
                raise ValidationError(f'Approved PO date cannot be greater than Bill draft date.')
            return False

        return True

    def can_generate_bill_number(self) -> bool:
        """
        Checks if BillModel can generate its Bill Number.
        @return: True/False as Boolean.
        """
        return all([
            not self.bill_number,
            self.date_draft,
            self.ledger_id
        ])

    # --> ACTIONS <---
    def action_bind_estimate(self, estimate_model, commit: bool = False, raise_exception: bool = True):
        """
        Binds BillModel to a given EstimateModel. Raises ValueError if
        @param raise_exception: Raises exception if unable to bind EstimateModel.
        @param estimate_model: EstimateModel to bind.
        @param commit: Commits transaction into current BillModel.
        @return: None
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

    def mark_as_draft(self, date_draft: date = None, commit: bool = False, **kwargs):
        """
        Marks BillModel as Draft.
        @param date_draft: Draft date. If None, defaults to localdate().
        @param commit: Commits transaction into the Database. Defaults to False.
        @param kwargs: Additional kwargs passed into the function.
        @return: None
        """
        if not self.can_draft():
            raise ValidationError(
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
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-draft'

    def get_mark_as_draft_url(self, entity_slug: str = None) -> str:
        """
        BillModel Mark-as-Draft action URL.
        @return: BillModel mark-as-draft action URL.
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
        @return: Mark-as-Draft BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Draft?') % self.bill_number

    # IN REVIEW ACTIONS....
    def mark_as_review(self,
                       commit: bool = False,
                       itemtxs_qs: ItemTransactionModelQuerySet = None,
                       date_in_review: date = None,
                       **kwargs):
        """
        Marks BillModel as In Review.
        @param commit: Commits transaction into the Database. Defaults to False.
        @param itemtxs_qs: Pre fetched ItemTransactionModelQuerySet to use. Avoids additional DB Query if previously fetched.
        @param date_in_review: BillModel in review date. Defaults to localdate() if None.
        @param kwargs: Additional function kwargs passed.
        @return: None
        """

        if not self.can_review():
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as in review. Must be Draft and Configured.'
            )

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()
        if not itemtxs_qs.count():
            raise ValidationError(message=f'Cannot review a {self.__class__.__name__} without items...')
        if not self.amount_due:
            raise ValidationError(
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
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-review'

    def get_mark_as_review_url(self, entity_slug: str = None) -> str:
        """
        BillModel Mark-as-Review action URL.
        @return: BillModel mark-as-review action URL.
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
        @return: Mark-as-Review BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as In Review?') % self.bill_number

    # APPROVED ACTIONS....
    def mark_as_approved(self,
                         user_model,
                         entity_slug: str = None,
                         approved_date: date = None,
                         commit: bool = False,
                         force_migrate: bool = False,
                         **kwargs):
        """
        Marks BillModel as Approved.
        @param entity_slug: Entity slug associated with the BillModel. Avoids additional DB query if passed.
        @param user_model: UserModel associated with request.
        @param approved_date: BillModel approved date. Defaults to localdate().
        @param commit: Commits transaction into the Database. Defaults to False.
        @param force_migrate: Forces migration. True if Accounting Method is Accrual.
        @param kwargs: Additional function kwargs passed.
        @return: None
        """

        if not self.can_approve():
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as in approved.'
            )
        self.bill_status = self.BILL_STATUS_APPROVED
        self.date_approved = localdate() if not approved_date else approved_date
        self.new_state(commit=True)
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
                    je_date=approved_date,
                    force_migrate=self.accrue
                )
            self.ledger.post(commit=commit)

    def get_mark_as_approved_html_id(self) -> str:
        """
        BillModel Mark as Approved HTML ID.
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-approved'

    def get_mark_as_approved_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Approved action URL.
        @return: BillModel mark-as-approved action URL.
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
        @return: Mark-as-Approved BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Approved?') % self.bill_number

    # DELETE ACTIONS...
    def mark_as_delete(self, **kwargs):
        """
        Deletes BillModel from DB if possible. Raises exception if can_delete() is False.
        @param kwargs: Additional function kwargs.
        @return:
        """
        if not self.can_delete():
            raise ValidationError(f'Bill {self.bill_number} cannot be deleted. Must be void after Approved.')
        self.delete(**kwargs)

    def get_mark_as_delete_html_id(self) -> str:
        """
        BillModel Mark as Delete HTML ID Tag.
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-delete'

    def get_mark_as_delete_url(self, entity_slug: Optional[str] = None) -> str:
        """
        BillModel Mark-as-Delete action URL.
        @return: BillModel mark-as-delete action URL.
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
        @return: Mark-as-Delete BillModel confirmation message as a String.
        """
        return _('Do you want to delete Bill %s?') % self.bill_number

    # PAY ACTIONS....
    def mark_as_paid(self,
                     user_model,
                     entity_slug: str = None,
                     date_paid: date = None,
                     itemtxs_qs=None,
                     commit: bool = False,
                     **kwargs):
        """

        @param entity_slug: Entity slug associated with the BillModel. Avoids additional DB query if passed.
        @param user_model: UserModel associated with request.
        @param date_paid: BillModel paid date. Defaults to localdate() if None.
        @param itemtxs_qs: Pre fetched ItemTransactionModelQuerySet. Avoids additional DB query.
        @param commit: Commits transaction into the Database. Defaults to False.
        @param kwargs: Additional function kwargs passed.
        @return None
        """

        if not self.can_pay():
            raise ValidationError(f'Cannot mark Bill {self.bill_number} as paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        self.date_paid = localdate() if not date_paid else date_paid

        if self.date_paid > localdate():
            raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        if self.date_paid < self.date_approved:
            raise ValidationError(f'Cannot pay {self.__class__.__name__} before approved date {self.date_approved}.')

        self.bill_status = self.BILL_STATUS_PAID
        self.new_state(commit=True)
        self.clean()

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()

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
                je_date=date_paid,
                force_migrate=True
            )
            self.lock_ledger(commit=True)

    def get_mark_as_paid_html_id(self) -> str:
        """
        BillModel Mark as Paid HTML ID Tag.
        @return: HTML ID as a String
        """
        return f'djl-bill-model-{self.uuid}-mark-as-paid'

    def get_mark_as_paid_url(self, entity_slug: Optional[str]) -> str:
        """
        BillModel Mark-as-Paid action URL.
        @return: BillModel mark-as-paid action URL.
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
        @return: Mark-as-Paid BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Paid?') % self.bill_number

    # VOID Actions...
    def mark_as_void(self,
                     user_model,
                     entity_slug: str = None,
                     void_date: date = None,
                     commit: bool = False,
                     **kwargs):
        """
        Marks BillModel as Void.
        When mark as void, all transactions associated with BillModel are reversed as of the void date.
        @param entity_slug: Entity slug associated with the BillModel. Avoids additional DB query if passed.
        @param user_model: UserModel associated with request.
        @param void_date: BillModel void date. Defaults to localdate() if None.
        @param commit: Commits transaction into DB. Defaults to False.
        @param kwargs: Additional function kwargs passed.
        @return: None
        """
        if not self.can_void():
            raise ValidationError(f'Bill {self.bill_number} cannot be voided. Must be approved.')

        self.date_void = void_date if void_date else localdate()
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
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-void'

    def get_mark_as_void_url(self, entity_slug: Optional[str]) -> str:
        """
        BillModel Mark-as-Void action URL.
        @return: BillModel mark-as-void action URL.
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
        @return: Mark-as-Void BillModel confirmation message as a String.
        """
        return _('Do you want to void Bill %s?') % self.bill_number

    # Cancel Actions...
    def mark_as_canceled(self, canceled_date: date, commit: bool = False, **kwargs):
        """
        Mark BillModel as Canceled.
        @param canceled_date: BillModel canceled date. Defaults to localdate() if None.
        @param commit: Commits transaction into the Database. Defaults to False.
        @param kwargs: Additional function kwargs passed.
        @return: None
        """
        if not self.can_cancel():
            raise ValidationError(f'Bill {self.bill_number} cannot be canceled. Must be draft or in review.')

        self.date_canceled = localdate() if not canceled_date else canceled_date
        self.bill_status = self.BILL_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'bill_status',
                'date_canceled'
            ])

    def get_mark_as_canceled_html_id(self) -> str:
        """
        Internationalized confirmation message with Bill Number.
        @return: Mark-as-Canceled BillModel confirmation message as a String.
        """
        return f'djl-bill-model-{self.uuid}-mark-as-canceled'

    def get_mark_as_canceled_url(self, entity_slug: Optional[str]) -> str:
        """
        BillModel Mark-as-Canceled action URL.
        @return: BillModel mark-as-canceled action URL.
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
        @return: Mark-as-Canceled BillModel confirmation message as a String.
        """
        return _('Do you want to mark Bill %s as Canceled?') % self.bill_number

    def get_status_action_date(self) -> date:
        """
        Current status action date.
        @return: A date. i.e. If status is Approved, return date_approved. If Paid, return date_paid.
        """
        return getattr(self, f'date_{self.bill_status}')

    # HTML Tags...
    def get_document_id(self) -> Optional[str]:
        """
        Human-readable document number. Defaults to bill_number.
        @return: Document Number as a String.
        """
        return self.bill_number

    def get_html_id(self) -> str:
        """
        Unique BillNumber HTML ID.
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}'

    def get_html_amount_due_id(self) -> str:
        """
        Unique amount due HTML ID.
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-amount-due'

    def get_html_amount_paid_id(self) -> str:
        """
        Unique amount paid HTML ID
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-amount-paid'

    def get_html_form_id(self) -> str:
        """
        Unique BillModel Form HTML ID.
        @return: HTML ID as a String.
        """
        return f'djl-bill-model-{self.uuid}-form'

    def get_terms_start_date(self) -> date:
        """
        Date where BillModel term start to apply.
        @return: A date which represents the start of terms.
        """
        return self.date_approved

    def _get_next_state_model(self, raise_exception: bool = True):
        EntityStateModel = lazy_loader.get_entity_state_model()
        EntityModel = lazy_loader.get_entity_model()
        entity_model = EntityModel.objects.get(uuid__exact=self.ledger.entity_id)
        fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

        try:
            LOOKUP = {
                'entity_id__exact': self.ledger.entity_id,
                'entity_unit_id__exact': None,
                'fiscal_year': fy_key,
                'key__exact': EntityStateModel.KEY_BILL
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_related('entity').select_for_update()
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
                'entity_id': entity_model.uuid,
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
        @param commit: Commit transaction into InvoiceModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
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

    def clean(self):
        if self.can_generate_bill_number():
            self.generate_bill_number(commit=True)

        super(LedgerWrapperMixIn, self).clean()
        super(PaymentTermsMixIn, self).clean()

        if self.accrue:
            self.progress = Decimal('1.00')

        if self.is_draft():
            self.amount_paid = Decimal('0.00')
            self.paid = False
            self.date_paid = None

        if not self.additional_info:
            self.additional_info = dict()

    def save(self, **kwargs):
        if self.can_generate_bill_number():
            self.generate_bill_number(commit=True)
        super(BillModelAbstract, self).save(**kwargs)


class BillModel(BillModelAbstract):
    """
    Base Bill Model from Abstract.
    """


def billmodel_predelete(instance: BillModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=billmodel_predelete, sender=BillModel)
