"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <Ptulshyan77@gmail.com>

A purchase order is a commercial source document that is issued by a business purchasing department when placing an
order with its vendors or suppliers. The document indicates the details on the items that are to be purchased, such as
the types of goods, quantity, and price. In simple terms, it is the contract drafted by the buyer when purchasing goods
from the seller.

The PurchaseOrderModel is designed to track the status of a Purchase Order and all its items. The PurchaseOrderModel
starts in draft model by default and goes through different states including InReview, Approved, Fulfilled, Canceled and
Void. The PurchaseOrderModel also keeps track of when these states take place.

"""
from datetime import date
from string import ascii_uppercase, digits
from typing import Tuple, List, Union, Optional
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinLengthValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, Count, F
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models.bill import BillModel, BillModelQuerySet
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModel, ItemTransactionModelQuerySet
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_PO_NUMBER_PREFIX

PO_NUMBER_CHARS = ascii_uppercase + digits

UserModel = get_user_model()


class PurchaseOrderModelValidationError(ValidationError):
    pass


class PurchaseOrderModelQuerySet(models.QuerySet):
    """
    A custom defined PurchaseOrderModel QuerySet.
    """

    def approved(self):
        """
        Filters the QuerySet to include Approved PurchaseOrderModels only.

        Returns
        -------
        PurchaseOrderModelQuerySet
            A PurchaseOrderModelQuerySet with applied filters.
        """
        return self.filter(po_status__exact=PurchaseOrderModel.PO_STATUS_APPROVED)

    def fulfilled(self):
        """
        Filters the QuerySet to include Fulfilled PurchaseOrderModels only.

        Returns
        -------
        PurchaseOrderModelQuerySet
            A PurchaseOrderModelQuerySet with applied filters.
        """
        return self.filter(po_status__exact=PurchaseOrderModel.PO_STATUS_FULFILLED)

    def active(self):
        """
        Filters the QuerySet to include Active PurchaseOrderModels only.
        Active PurchaseOrderModels are either approved or fulfilled, which are those that may contain associated
        transactions on the Ledger.

        Returns
        -------
        PurchaseOrderModelQuerySet
            A PurchaseOrderModelQuerySet with applied filters.
        """
        return self.filter(
            Q(po_status__exact=PurchaseOrderModel.PO_STATUS_APPROVED) |
            Q(po_status__exact=PurchaseOrderModel.PO_STATUS_FULFILLED)
        )


class PurchaseOrderModelManager(models.Manager):
    """
    A custom defined PurchaseOrderModel Manager.
    """

    def for_entity(self, entity_slug, user_model) -> PurchaseOrderModelQuerySet:
        """
        Fetches a QuerySet of PurchaseOrderModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Returns
        -------
        PurchaseOrderModelQuerySet
            A PurchaseOrderModelQuerySet with applied filters.
        """
        qs = self.get_queryset()
        if isinstance(entity_slug, EntityModel):
            qs = qs.filter(entity=entity_slug)
        elif isinstance(entity_slug, str):
            qs = qs.filter(entity__slug__exact=entity_slug)
        return qs.filter(
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )


class PurchaseOrderModelAbstract(CreateUpdateMixIn, MarkdownNotesMixIn):
    """
    The base implementation of the PurchaseOrderModel.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    po_number: str
        A unique human-readable and sequential PO Number identifier. Automatically generated.
    po_title: str
        The PurchaseOrderModel instance title.
    po_status: str
        One of PO_STATUS values representing the current status of the PurchaseOrderModel instance.
    po_amount: Decimal
        The total value of the PurchaseOrderModel instance.
    po_amount_received: Decimal
        The PurchaseOrderModel instance total value received to date. Cannot be greater than PO amount.
    entity: EntityModel
        The EntityModel associated with the PurchaseOrderModel instance.
    date_draft: date
        The draft date represents the date when the PurchaseOrderModel was first created. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.
    date_in_review: date
        The in review date represents the date when the PurchaseOrderModel was marked as In Review status.
        Will be null if PurchaseOrderModel is canceled during draft status. Defaults to
        :func:`localdate <django.utils.timezone.localdate>`.
    date_approved: date
        The approved date represents the date when the PurchaseOrderModel was approved. Will be null if
        PurchaseOrderModel is canceled.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_fulfilled: date
        The paid date represents the date when the PurchaseOrderModel was fulfilled and po_amount_received equals
        po_amount. Will be null if PurchaseOrderModel is canceled.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_void: date
        The void date represents the date when the PurchaseOrderModel was void, if applicable.
        Will be null unless PurchaseOrderModel is void.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    date_canceled: date
        The canceled date represents the date when the PurchaseOrderModel was canceled, if applicable.
        Will be null unless PurchaseOrderModel is canceled.
        Defaults to :func:`localdate <django.utils.timezone.localdate>`.
    po_items:
        A foreign key reference to the list of ItemTransactionModel that make the PurchaseOrderModel amount.
    ce_model: EstimateModel
        A foreign key reference to the EstimateModel associated with the PurchaseOrderModel, if any.
    """
    PO_STATUS_DRAFT = 'draft'
    PO_STATUS_REVIEW = 'in_review'
    PO_STATUS_APPROVED = 'approved'
    PO_STATUS_FULFILLED = 'fulfilled'
    PO_STATUS_VOID = 'void'
    PO_STATUS_CANCELED = 'canceled'

    """The different valid PO Status and their representation in the Database"""
    PO_STATUS = [
        (PO_STATUS_DRAFT, _('Draft')),
        (PO_STATUS_REVIEW, _('In Review')),
        (PO_STATUS_APPROVED, _('Approved')),
        (PO_STATUS_FULFILLED, _('Fulfilled')),
        (PO_STATUS_CANCELED, _('Canceled')),
        (PO_STATUS_VOID, _('Void')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_number = models.SlugField(max_length=20, verbose_name=_('Purchase Order Number'), editable=False)
    po_title = models.CharField(max_length=250,
                                verbose_name=_('Purchase Order Title'),
                                validators=[
                                    MinLengthValidator(limit_value=5,
                                                       message=_(
                                                           f'PO Title must be greater than 5'))
                                ])
    po_status = models.CharField(max_length=10, choices=PO_STATUS, default=PO_STATUS[0][0])
    po_amount = models.DecimalField(default=0, decimal_places=2, max_digits=20, verbose_name=_('Purchase Order Amount'))
    po_amount_received = models.DecimalField(default=0,
                                             decimal_places=2,
                                             max_digits=20,
                                             verbose_name=_('Received Amount'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'))

    date_draft = models.DateField(null=True, blank=True, verbose_name=_('Draft Date'))
    date_in_review = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    date_approved = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    date_void = models.DateField(blank=True, null=True, verbose_name=_('Void Date'))
    date_fulfilled = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))
    date_canceled = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

    po_items = models.ManyToManyField('django_ledger.ItemModel',
                                      through='django_ledger.ItemTransactionModel',
                                      through_fields=('po_model', 'item_model'),
                                      verbose_name=_('Purchase Order Items'))

    ce_model = models.ForeignKey('django_ledger.EstimateModel',
                                 on_delete=models.RESTRICT,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Associated Customer Job/Estimate'))

    objects = PurchaseOrderModelManager.from_queryset(queryset_class=PurchaseOrderModelQuerySet)()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity']),
            models.Index(fields=['po_number']),
            models.Index(fields=['po_status']),
            models.Index(fields=['ce_model']),

            models.Index(fields=['date_draft']),
            models.Index(fields=['date_in_review']),
            models.Index(fields=['date_approved']),
            models.Index(fields=['date_fulfilled']),
            models.Index(fields=['date_canceled']),
            models.Index(fields=['date_void']),
        ]
        unique_together = [
            ('entity', 'po_number')
        ]

    def __str__(self):
        # pylint: disable=no-member
        return f'PO Model: {self.po_number} | {self.get_po_status_display()}'

    # Configuration...

    def is_configured(self) -> bool:
        return all([
            self.entity_id is not None,
            self.date_draft,
            self.po_status
        ])

    def configure(self,
                  entity_slug: Union[str, EntityModel],
                  po_title: Optional[str] = None,
                  user_model: Optional[UserModel] = None,
                  draft_date: Optional[date] = None,
                  estimate_model=None,
                  commit: bool = False):
        """
        A configuration hook which executes all initial PurchaseOrderModel setup on to the EntityModel and all initial
        values of the EntityModel. Can only call this method once in the lifetime of a PurchaseOrderModel.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel to associate the Bill with.
        user_model:
            The UserModel making the request to check for QuerySet permissions.
        ledger_posted:
            An option to mark the BillModel Ledger as posted at the time of configuration. Defaults to False.
        bill_desc: str
            An optional description appended to the LedgerModel name.
        commit: bool
            Saves the current BillModel after being configured.

        Returns
        -------
        PurchaseOrderModel
            The configured PurchaseOrderModel instance.
        """
        if not self.is_configured():
            if isinstance(entity_slug, str):
                if not user_model:
                    raise PurchaseOrderModelValidationError(_('Must pass user_model when using entity_slug.'))
                entity_qs = EntityModel.objects.for_user(user_model=user_model)
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
            elif isinstance(entity_slug, EntityModel):
                entity_model = entity_slug
            else:
                raise PurchaseOrderModelValidationError('entity_slug must be an instance of str or EntityModel')

            self.date_draft = localdate() if not draft_date else draft_date
            self.po_status = PurchaseOrderModel.PO_STATUS_DRAFT

            if estimate_model:
                self.action_bind_estimate(estimate_model=estimate_model, commit=False)

            self.entity = entity_model

            if self.can_generate_po_number():
                self.generate_po_number(commit=commit)

            if not po_title and not self.po_title and self.po_number:
                self.po_title = f'PO Number {self.po_number}'
            else:
                self.po_title = po_title

            self.clean()
            self.clean_fields()
            if commit:
                self.save()
        return self

    def validate_item_transaction_qs(self, queryset: Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]]):
        """
        Validates that the entire ItemTransactionModelQuerySet is bound to the PurchaseOrderModel.

        Parameters
        ----------
        queryset: ItemTransactionModelQuerySet or list of ItemTransactionModel.
            ItemTransactionModelQuerySet to validate.
        """
        valid = all([
            i.po_model_id == self.uuid for i in queryset
        ])
        if not valid:
            raise PurchaseOrderModelValidationError(f'Invalid queryset. All items must be assigned to PO {self.uuid}')

    # State Update...
    def get_itemtxs_data(self,
                         queryset: Optional[Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]]] = None,
                         aggregate_on_db: bool = False) -> Tuple:
        """
        Fetches the PurchaseOrderModel Items and aggregates the QuerySet.

        Parameters
        ----------
        queryset: ItemTransactionModelQuerySet
            Optional pre-fetched ItemModelQueryset to use. Avoids additional DB query if provided.
            Validated if provided.
        aggregate_on_db: bool
            If True, performs aggregation of ItemsTransactions in the DB resulting in one additional DB query.

        Returns
        -------
        A tuple: ItemTransactionModelQuerySet, dict
        """
        if not queryset:
            queryset = self.itemtransactionmodel_set.all().select_related('bill_model', 'item_model')
        else:
            self.validate_item_transaction_qs(queryset)

        if aggregate_on_db and isinstance(queryset, ItemTransactionModelQuerySet):
            return queryset, queryset.aggregate(
                po_total_amount__sum=Coalesce(Sum('po_total_amount'), 0.0, output_field=models.FloatField()),
                bill_amount_paid__sum=Coalesce(Sum('bill_model__amount_paid'), 0.0, output_field=models.FloatField()),
                total_items=Count('uuid')
            )
        return queryset, {
            'po_total_amount__sum': sum(i.total_amount for i in queryset),
            'bill_amount_paid__sum': sum(i.bill_model.amount_paid for i in queryset if i.bill_model_id),
            'total_items': len(queryset)
        }

    def update_state(self,
                     itemtxs_qs: Optional[Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]]] = None
                     ) -> Tuple:

        """
        Updates the state of the PurchaseOrderModel.

        Parameters
        ----------
        itemtxs_qs: ItemTransactionModelQuerySet or list of ItemTransactionModel

        Returns
        -------
        tuple
            A tuple of ItemTransactionModels and Aggregation
        """
        itemtxs_qs, itemtxs_agg = self.get_itemtxs_data(queryset=itemtxs_qs)

        if isinstance(itemtxs_qs, list):
            self.po_amount = round(sum(a.po_total_amount for a in itemtxs_qs if not a.is_canceled()), 2)
            self.po_amount_received = round(sum(a.po_total_amount for a in itemtxs_qs if a.is_received()), 2)
        elif isinstance(itemtxs_qs, ItemTransactionModelQuerySet):
            total_po_amount = round(sum(i.po_total_amount for i in itemtxs_qs if not i.is_canceled()), 2)
            total_received = round(sum(i.po_total_amount for i in itemtxs_qs if i.is_received()), 2)
            self.po_amount = total_po_amount
            self.po_amount_received = total_received

        return itemtxs_qs, itemtxs_agg

    # State...
    def is_draft(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Draft status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is Draft, else False.
        """
        return self.po_status == self.PO_STATUS_DRAFT

    def is_review(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Review status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is Review, else False.
        """
        return self.po_status == self.PO_STATUS_REVIEW

    def is_approved(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Approved status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is Approved, else False.
        """
        return self.po_status == self.PO_STATUS_APPROVED

    def is_fulfilled(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Fulfilled status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is in Fulfilled status, else False.
        """
        return self.po_status == self.PO_STATUS_FULFILLED

    def is_canceled(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Canceled status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is in Canceled, else False.
        """
        return self.po_status == self.PO_STATUS_CANCELED

    def is_void(self) -> bool:
        """
        Checks if the PurchaseOrderModel is in Void status.

        Returns
        -------
        bool
            True if PurchaseOrderModel is Void, else False.
        """
        return self.po_status == self.PO_STATUS_VOID

    # Permissions...
    def can_draft(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as Draft.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as Draft, else False.
        """
        return self.is_review()

    def can_review(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as In Review.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as In Review, else False.
        """
        return self.is_draft()

    def can_approve(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as Approved.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as Approved, else False.
        """
        return self.is_review()

    def can_fulfill(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as Fulfilled.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as Fulfilled, else False.
        """
        return self.is_approved()

    def can_cancel(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as Canceled.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as Canceled, else False.
        """
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_void(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be marked as Void.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be marked as Void, else False.
        """
        return self.is_approved()

    def can_delete(self) -> bool:
        """
        Checks if the PurchaseOrderModel can be deleted.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be deleted, else False.
        """
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self) -> bool:
        """
        Checks if the PurchaseOrderModel items can be edited.

        Returns
        -------
        bool
            True if PurchaseOrderModel items can be edited, else False.
        """
        return self.is_draft()

    def is_contract_bound(self):
        """
        Checks if the PurchaseOrderModel is bound to an EstimateModel.

        Returns
        -------
        bool
            True if PurchaseOrderModel is bound to an EstimateModel, else False.
        """
        return self.ce_model_id is not None

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        """
        Checks if the PurchaseOrderModel ican be bound to an EstimateModel.

        Returns
        -------
        bool
            True if PurchaseOrderModel can be bound to an EstimateModel, else False.
        """
        if self.is_contract_bound():
            if raise_exception:
                raise PurchaseOrderModelValidationError(
                    f'PO {self.po_number} already bound to Estimate {self.ce_model.estimate_number}')
            return False
        elif self.entity_id != estimate_model.entity_id:
            if raise_exception:
                raise PurchaseOrderModelValidationError(
                    f'Invalid EstimateModel for entity {self.entity.slug}'
                )
            return False

        # check if estimate_model is passed and raise exception if needed...
        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise PurchaseOrderModelValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    def action_bind_estimate(self, estimate_model, commit: bool = False):
        """
        Binds a specific EstimateModel to the PurchaseOrderModel instance.

        Parameters
        ----------
        estimate_model: EstimateModel
            The EstimateModel to bind.
        commit: bool
            Commits the changes in the Database, if True. Defaults to False.
        """
        try:
            self.can_bind_estimate(estimate_model, raise_exception=True)
        except ValueError as e:
            raise e
        self.ce_model = estimate_model
        self.clean()
        if commit:
            self.save(update_fields=[
                'ce_model',
                'updated'
            ])

    def can_generate_po_number(self):
        """
        Checks if PurchaseOrderModel can generate its Document Number.

        Returns
        -------
        bool
            True if PurchaseOrderModel can generate its po_number, else False.
        """
        return all([
            self.date_draft,
            not self.po_number
        ])

    # Actions...

    # DRAFT...
    def mark_as_draft(self, date_draft: Optional[date] = None, commit: bool = False, **kwargs):
        """
        Marks PurchaseOrderModel as Draft.

        Parameters
        ----------
        date_draft: date
            Draft date. If None, defaults to localdate().
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_draft():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as draft.')
        self.po_status = self.PO_STATUS_DRAFT
        self.date_draft = localdate() if not date_draft else date_draft
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def get_mark_as_draft_html_id(self):
        """
        PurchaseOrderModel Mark as Draft HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-draft'

    def get_mark_as_draft_url(self):
        """
        PurchaseOrderModel Mark as Draft URL ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return reverse('django_ledger:po-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        """
        PurchaseOrderModel Mark as Draft Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as Draft?') % self.po_number

    # REVIEW...
    def mark_as_review(self, date_in_review: Optional[date] = None, commit: bool = False, **kwargs):
        """
        Marks PurchaseOrderModel as In Review.

        Parameters
        ----------
        date_in_review: date
            Draft date. If None, defaults to localdate().
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_review():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as in review.')

        itemtxs_qs, itemtxs_agg = self.get_itemtxs_data()
        if not itemtxs_qs.count():
            raise PurchaseOrderModelValidationError(message='Cannot review a PO without items...')
        if not self.po_amount:
            raise PurchaseOrderModelValidationError(message='PO amount is zero.')

        self.date_in_review = localdate() if not date_in_review else date_in_review
        self.po_status = self.PO_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'date_in_review',
                'updated'
            ])

    def get_mark_as_review_html_id(self):
        """
        PurchaseOrderModel Mark as In Review HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-review'

    def get_mark_as_review_url(self):
        """
        PurchaseOrderModel Mark as In Review URL ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return reverse('django_ledger:po-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        """
        PurchaseOrderModel Mark as Review Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as In Review?') % self.po_number

    # APPROVED...
    def mark_as_approved(self, date_approved: Optional[date] = None, commit: bool = False, **kwargs):
        """
        Marks PurchaseOrderModel as Approved.

        Parameters
        ----------
        date_approved: date
            Approved date. If None, defaults to localdate().
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_approve():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as approved.')
        self.date_approved = localdate() if not date_approved else date_approved
        self.po_status = self.PO_STATUS_APPROVED
        self.clean()
        if commit:
            self.itemtransactionmodel_set.all().update(po_item_status=ItemTransactionModel.STATUS_NOT_ORDERED)
            self.save(update_fields=[
                'date_approved',
                'po_status',
                'updated'
            ])

    def get_mark_as_approved_html_id(self):
        """
        PurchaseOrderModel Mark as Approved HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-approved'

    def get_mark_as_approved_url(self):
        """
        PurchaseOrderModel Mark as Approved URL ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return reverse('django_ledger:po-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        """
        PurchaseOrderModel Mark as Approved Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as Approved?') % self.po_number

    # CANCEL...
    def mark_as_canceled(self, date_canceled: Optional[date] = None, commit: bool = False, **kwargs):
        """
        Marks PurchaseOrderModel as Canceled.

        Parameters
        ----------
        date_canceled: date
            Canceled date. If None, defaults to localdate().
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_cancel():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as canceled.')
        self.date_canceled = localdate() if not date_canceled else date_canceled
        self.po_status = self.PO_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'date_canceled',
                'updated'
            ])

    def get_mark_as_canceled_html_id(self):
        """
        PurchaseOrderModel Mark as Canceled HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        """
        PurchaseOrderModel Mark as Canceled URL ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return reverse('django_ledger:po-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        """
        PurchaseOrderModel Mark as Canceled Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as Canceled?') % self.po_number

    # FULFILL...
    def mark_as_fulfilled(self,
                          date_fulfilled: date = None,
                          po_items: Union[ItemTransactionModelQuerySet, List[ItemTransactionModel]] = None,
                          commit: bool = False,
                          **kwargs):
        """
        Marks PurchaseOrderModel as Fulfilled.

        Parameters
        ----------
        date_fulfilled: date
            Fulfilled date. If None, defaults to localdate().
        po_items: ItemTransactionModelQuerySet or list of ItemTransactionModel.
            Pre-fetched ItemTransactionModelQuerySet or list of  ItemTransactionModel.
            Validated if provided.
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """

        if not self.can_fulfill():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as fulfilled.')

        if not po_items:
            po_items, po_items_agg = self.get_itemtxs_data(queryset=po_items)

        self.date_fulfilled = localdate() if not date_fulfilled else date_fulfilled
        self.po_amount_received = self.po_amount

        bill_models = [i.bill_model for i in po_items]
        all_items_billed = all(bill_models)
        if not all_items_billed:
            raise PurchaseOrderModelValidationError('All items must be billed before PO can be fulfilled.')

        all_bills_paid = all(b.is_paid() for b in bill_models)
        if not all_bills_paid:
            raise PurchaseOrderModelValidationError('All Bills must be paid before PO can be fulfilled.')

        all_items_received = all(i.is_received() for i in po_items)
        if not all_items_received:
            raise PurchaseOrderModelValidationError('All items must be received before PO is fulfilled.')

        self.date_fulfilled = date_fulfilled
        self.po_status = self.PO_STATUS_FULFILLED
        self.clean()

        if commit:
            # todo: what if PO items is list???...
            po_items.update(po_item_status=ItemTransactionModel.STATUS_RECEIVED)
            self.save(update_fields=[
                'date_fulfilled',
                'po_status',
                'updated'
            ])

    def get_mark_as_fulfilled_html_id(self):
        """
        PurchaseOrderModel Mark as Fulfilled HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-fulfilled'

    def get_mark_as_fulfilled_url(self):
        """
        PurchaseOrderModel Mark as Fulfilled URL ID Tag.

        Returns
        -------
        str
            URL as a String.
        """
        return reverse('django_ledger:po-action-mark-as-fulfilled',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_fulfilled_message(self):
        """
        PurchaseOrderModel Mark as Fulfilled Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as Fulfilled?') % self.po_number

    # VOID...
    def mark_as_void(self,
                     void_date: Optional[date] = None,
                     commit: bool = False,
                     **kwargs):
        """
        Marks PurchaseOrderModel as Fulfilled.

        Parameters
        ----------
        void_date: date
            Void date. If None, defaults to localdate().
        commit: bool
            Commits transaction into the Database. Defaults to False.
        """
        if not self.can_void():
            raise PurchaseOrderModelValidationError(
                message=f'Purchase Order {self.po_number} cannot be marked as void.')

        # all bills associated with this PO...
        bill_model_qs = self.get_po_bill_queryset()
        bill_model_qs = bill_model_qs.only('bill_status')

        if not all(b.is_void() for b in bill_model_qs):
            raise PurchaseOrderModelValidationError('Must void all PO bills before PO can be voided.')

        self.date_void = localdate() if not void_date else void_date
        self.po_status = self.PO_STATUS_VOID
        self.clean()

        if commit:
            self.save(update_fields=[
                'void_date',
                'po_status',
                'updated'
            ])

    def get_mark_as_void_html_id(self):
        """
        PurchaseOrderModel Mark as Void HTML ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return f'djl-{self.uuid}-po-mark-as-void'

    def get_mark_as_void_url(self):
        """
        PurchaseOrderModel Mark as Void URL ID Tag.

        Returns
        -------
        str
            HTML ID as a String.
        """
        return reverse('django_ledger:po-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        """
        PurchaseOrderModel Mark as Void Message.

        Returns
        -------
        str
            Message as a String.
        """
        return _('Do you want to mark Purchase Order %s as Void?') % self.po_number

    def get_po_bill_queryset(self) -> BillModelQuerySet:
        """
        Fetches a BillModelQuerySet of all BillModels associated with the PurchaseOrderModel instance.

        Returns
        -------
        BillModelQuerySet
        """
        return BillModel.objects.filter(bill_items__purchaseordermodel__uuid__exact=self.uuid)

    def get_status_action_date(self):
        """
        Current status action date.

        Returns
        -------
        date
            A date. i.e. If status is Approved, return date_approved. If In Review, return date_in_review.
        """
        return getattr(self, f'date_{self.po_status}')

    def _get_next_state_model(self, raise_exception: bool = True):
        """
        Fetches the next sequenced state model associated with the PurchaseOrderModel number.

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
        entity_model = EntityModel.objects.get(uuid__exact=self.entity_id)
        fy_key = entity_model.get_fy_for_date(dt=self.date_draft)
        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_id,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key__exact': EntityStateModel.KEY_PURCHASE_ORDER
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
            entity_model = EntityModel.objects.get(uuid__exact=self.entity_id)
            fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

            LOOKUP = {
                'entity_model_id': entity_model.uuid,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key': EntityStateModel.KEY_PURCHASE_ORDER,
                'sequence': 1
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_po_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next PurchaseOrder document number available.

        Parameters
        ----------
        commit: bool
            Commits transaction into PurchaseOrderModel.

        Returns
        -------
        str
            A String, representing the generated or current PurchaseOrderModel instance Document Number.
        """
        if self.can_generate_po_number():
            with transaction.atomic(durable=True):

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

                seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
                self.po_number = f'{DJANGO_LEDGER_PO_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'

                if commit:
                    self.save(update_fields=['po_number'])

        return self.po_number

    def clean(self):
        if self.can_generate_po_number():
            self.generate_po_number(commit=True)


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """


def purchaseordermodel_presave(instance: PurchaseOrderModel, **kwargs):
    if instance.can_generate_po_number():
        instance.generate_po_number(commit=False)


pre_save.connect(receiver=purchaseordermodel_presave, sender=PurchaseOrderModel)
