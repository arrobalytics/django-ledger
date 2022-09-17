"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import date
from decimal import Decimal
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count
from django.db.models.signals import post_delete
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import LazyLoader
from django_ledger.models.entity import EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn, LedgerWrapperMixIn, MarkdownNotesMixIn, PaymentTermsMixIn

UserModel = get_user_model()

lazy_loader = LazyLoader()

INVOICE_NUMBER_CHARS = ascii_uppercase + digits

"""
Invoice : it refers the Sales Invoice/ Sales Bill/ Tax Invoice/ Proof of Sale which the entity issues to its cutomers for the supply of goods or services
The model manages all the Sales Invoices  which are issued by the entity
In addition to tracking the invoice amount , it tracks the receipt and due amount


"""


def generate_invoice_number(length: int = 10, prefix: bool = True) -> str:
    """
    A function that generates a random bill identifier for new bill models.
    :param prefix:
    :param length: The length of the bill number.
    :return: A string representing a random bill identifier.
    """
    invoice_number = ''.join(choices(INVOICE_NUMBER_CHARS, k=length))
    if prefix:
        invoice_number = 'I-' + invoice_number
    return invoice_number


class InvoiceModelQuerySet(models.QuerySet):

     """
    A custom defined Query Set for the InvoiceModel.
    This implements multiple methods or queries that we need to run to get a status of Invoices raised by the entity.
    For e.g : We might want to have list of bills which are paid, unpaid, Due , OverDue, Approved, In draft stage.
    All these separate functions will assist in making such queries and building customized reports.

    """


    def paid(self):
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_PAID)

    def approved(self):
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED)

    def active(self):
        return self.filter(
            Q(invoice_status__exact=InvoiceModel.INVOICE_STATUS_PAID) |
            Q(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED)
        )


class InvoiceModelManager(models.Manager):

    """
    A custom defined Invoice Model Manager that will act as an inteface to handling the DB queries to the Invoice  Model.
    The default "get_queryset" has been overridden to refer the customdefined "InvoiceModelQuerySet"

    """

    def get_queryset(self):
        return InvoiceModelQuerySet(self.model, using=self._db)

    def for_entity(self, entity_slug, user_model):
        qs = self.get_queryset().filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )
        if isinstance(entity_slug, EntityModel):
            return qs.filter(ledger__entity=entity_slug)
        elif isinstance(entity_slug, str):
            return qs.filter(ledger__entity__slug__exact=entity_slug)

    def for_entity_unpaid(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.approved()


class InvoiceModelAbstract(LedgerWrapperMixIn,
                           PaymentTermsMixIn,
                           MarkdownNotesMixIn,
                           CreateUpdateMixIn):


    """
    This is the main abstract class which the Bill Model database will inherit, and it contains the fields/columns/attributes which the said table will have.
    In addition to the attributes mentioned below, it also has the the fields/columns/attributes mentioned in below MixIn:
    
    LedgerWrapperMixIn
    PaymentTermsMixIn
    MarkdownNotesMixIn
    CreateUpdateMixIn
    
    Read about these mixin here.

    Below are the fields specific to the bill model.
    @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the unique uuid generated.
    @bill_number: This is a slug  Field and hence a random bill number with Max Length of 20 will be defined
    @bill_status: Any bill can have the status as either of the choices as mentioned under "BILL_STATUS" By default , the status will be "Draft"
    @xref: this is the fiedl for capturing of any External reference number like the PO number of the buyer.Any othere reference number like the Vendor code in buyer books may also be captured.
    

    
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

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    invoice_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Invoice Number'))
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

    draft_date = models.DateField(null=True, blank=True, verbose_name=_('Draft Date'))
    in_review_date = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    approved_date = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    paid_date = models.DateField(null=True, blank=True, verbose_name=_('Paid Date'))
    void_date = models.DateField(null=True, blank=True, verbose_name=_('Void Date'))
    canceled_date = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['invoice_status']),
            models.Index(fields=['terms']),
            models.Index(fields=['customer']),

            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),

            models.Index(fields=['draft_date']),
            models.Index(fields=['in_review_date']),
            models.Index(fields=['approved_date']),
            models.Index(fields=['paid_date']),
            models.Index(fields=['void_date']),
            models.Index(fields=['canceled_date']),
        ]

    def __str__(self):
        return f'Invoice: {self.invoice_number}'

    def configure(self,
                  entity_slug: str or EntityModel,
                  user_model: UserModel,
                  post_ledger: bool = False):

        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        if entity_model.is_accrual_method():
            self.accrue = True
            self.progress = 1
        else:
            self.accrue = False

        LedgerModel = lazy_loader.get_ledger_model()
        ledger_model = LedgerModel.objects.create(
            entity=entity_model,
            posted=post_ledger,
            name=f'Invoice {self.invoice_number}',
        )
        ledger_model.clean()
        self.clean()
        self.ledger = ledger_model
        return ledger_model, self

    # STATE...
    def is_draft(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_DRAFT

    def is_review(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_REVIEW

    def is_approved(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_APPROVED

    def is_paid(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_PAID

    def is_canceled(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_CANCELED

    def is_void(self) -> bool:
        return self.invoice_status == self.INVOICE_STATUS_VOID

    # PERMISSIONS....
    def can_draft(self):
        return self.is_review()

    def can_review(self):
        return all([
            self.is_configured(),
            self.is_draft()
        ])

    def can_approve(self):
        return self.is_review()

    def can_pay(self):
        return self.is_approved()

    def can_cancel(self):
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_void(self):
        return self.is_approved()

    def can_delete(self):
        return any([
            self.is_review(),
            self.is_draft()
        ])

    def can_edit_items(self):
        return self.is_draft()

    def can_migrate(self):
        if not self.is_approved():
            return False
        return super(InvoiceModelAbstract, self).can_migrate()

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        if self.ce_model_id:
            if raise_exception:
                raise ValidationError(f'Invoice {self.invoice_number} already bound to '
                                      f'Estimate {self.ce_model.estimate_number}')
            return False

        if self.customer_id:
            if raise_exception:
                raise ValidationError(f'Cannot bind estimate {estimate_model.estimate_number} '
                                      f'Invoice model already has a customer {self.customer}')
            return False

        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise ValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    # ACTIONS...
    def action_bind_estimate(self, estimate_model, commit: bool = False):
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
    def mark_as_draft(self, commit: bool = False, **kwargs):
        if not self.can_draft():
            raise ValidationError(f'Cannot mark PO {self.uuid} as draft...')
        self.invoice_status = self.INVOICE_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
                'updated'
            ])

    def get_mark_as_draft_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-draft'

    def get_mark_as_draft_url(self):
        return reverse('django_ledger:invoice-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        return _('Do you want to mark Invoice %s as Draft?') % self.invoice_number

    # REVIEW...
    def mark_as_review(self,
                       date_in_review: date = None,
                       itemtxs_qs=None,
                       commit: bool = False, **kwargs):
        if not self.can_review():
            raise ValidationError(f'Cannot mark PO {self.uuid} as In Review...')

        self.in_review_date = localdate() if not date_in_review else date_in_review

        if not itemtxs_qs:
            itemtxs_qs = self.itemtransactionmodel_set.all()
        if not itemtxs_qs.count():
            raise ValidationError(message='Cannot review an Invoice without items...')
        if not self.amount_due:
            raise ValidationError(
                f'PO {self.invoice_number} cannot be marked as in review. Amount due must be greater than 0.'
            )

        self.invoice_status = self.INVOICE_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
                'in_review_date',
                'updated'
            ])

    def get_mark_as_review_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-review'

    def get_mark_as_review_url(self):
        return reverse('django_ledger:invoice-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        return _('Do you want to mark Invoice %s as In Review?') % self.invoice_number

    # APPROVED...
    def mark_as_approved(self, date_approved: date = None, commit: bool = False, **kwargs):
        if not self.can_approve():
            raise ValidationError(f'Cannot mark PO {self.uuid} as Approved...')

        self.invoice_status = self.INVOICE_STATUS_APPROVED
        self.approved_date = localdate() if not date_approved else date_approved
        self.clean()
        if commit:
            self.ledger.post(commit=True)
            self.save(update_fields=[
                'invoice_status',
                'approved_date',
                'due_date',
                'updated'
            ])

    def get_mark_as_approved_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-approved'

    def get_mark_as_approved_url(self):
        return reverse('django_ledger:invoice-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        return _('Do you want to mark Invoice %s as Approved?') % self.invoice_number

    # PAID...
    def mark_as_paid(self,
                     entity_slug: str,
                     user_model,
                     date_paid: date = None,
                     commit: bool = False,
                     **kwargs):
        if not self.can_pay():
            raise ValidationError(f'Cannot mark PO {self.uuid} as Paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        self.paid_date = localdate() if not date_paid else date_paid

        if self.paid_date > localdate():
            raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')

        self.new_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_PAID
        self.clean()

        if commit:
            self.save()
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                force_migrate=True,
                je_date=date_paid
            )
            self.lock_ledger(commit=True)

    def get_mark_as_paid_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-paid'

    def get_mark_as_paid_url(self):
        return reverse('django_ledger:invoice-action-mark-as-paid',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_paid_message(self):
        return _('Do you want to mark Invoice %s as Paid?') % self.invoice_number

    # VOID...
    def mark_as_void(self,
                     entity_slug: str,
                     user_model,
                     date_void: date = None,
                     commit: bool = False,
                     **kwargs):

        if not self.can_void():
            raise ValidationError(f'Cannot mark Invoice {self.uuid} as Void...')

        self.void_date = localdate() if not date_void else date_void

        if self.void_date > localdate():
            raise ValidationError(f'Cannot void {self.__class__.__name__} in the future.')
        if self.void_date < self.approved_date:
            raise ValidationError(f'Cannot void {self.__class__.__name__} before approved {self.approved_date}')

        self.void_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_VOID
        self.clean()

        if commit:
            self.unlock_ledger(commit=True, raise_exception=False)
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                void=True,
                void_date=self.void_date,
                force_migrate=False,
                raise_exception=False
            )
            self.save()
            self.lock_ledger(commit=True, raise_exception=False)

    def get_mark_as_void_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-void'

    def get_mark_as_void_url(self):
        return reverse('django_ledger:invoice-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        return _('Do you want to mark Invoice %s as Void?') % self.invoice_number

    # CANCEL
    def mark_as_canceled(self, date_canceled: date = None, commit: bool = False, **kwargs):
        if not self.can_cancel():
            raise ValidationError(f'Cannot cancel Invoice {self.invoice_number}.')

        self.canceled_date = localdate() if not date_canceled else date_canceled
        self.invoice_status = self.INVOICE_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
                'canceled_date',
                'updated'
            ])
            self.lock_ledger(commit=True, raise_exception=False)
            self.unpost_ledger(commit=True, raise_exception=False)

    def get_mark_as_canceled_html_id(self):
        return f'djl-{self.uuid}-invoice-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        return reverse('django_ledger:invoice-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        return _('Do you want to mark Invoice %s as Canceled?') % self.invoice_number

    # ACTIONS END....

    def get_status_action_date(self):
        return getattr(self, f'{self.invoice_status}_date')

    def get_html_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_html_amount_due_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}-amount-due'

    def get_html_amount_paid_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}-amount-paid'

    def get_html_form_name(self):
        return f'djl-form-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_document_id(self):
        return self.invoice_number

    def get_mark_paid_url(self, entity_slug):
        return reverse('django_ledger:invoice-mark-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': self.uuid
                       })

    def get_migrate_state_desc(self):
        """
        Must be implemented.
        :return:
        """
        return f'Invoice {self.invoice_number} account adjustment.'

    def get_itemtxs_data(self, queryset=None) -> tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.all().select_related('item_model')
        return queryset, queryset.aggregate(
            Sum('total_amount'),
            total_items=Count('uuid')
        )

    def can_migrate(self) -> bool:
        return self.is_approved()

    def get_item_data(self, entity_slug: str, queryset=None):
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.all()
            queryset = queryset.filter(invoice_model__ledger__entity__slug__exact=entity_slug)
        return queryset.select_related('item_model').order_by('item_model__earnings_account__uuid',
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

    def update_amount_due(self, itemtxs_qs=None, itemtxs_list: list = None) -> None or tuple:
        if itemtxs_list:
            # self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            self.amount_due = round(sum(a.total_amount for a in itemtxs_list), 2)
            return
        itemtxs_qs, itemtxs_agg = self.get_itemtxs_data(queryset=itemtxs_qs)
        self.amount_due = round(itemtxs_agg['total_amount__sum'], 2)
        return itemtxs_qs, itemtxs_agg

    def get_terms_start_date(self) -> date:
        return self.approved_date

    def clean(self):
        super(LedgerWrapperMixIn, self).clean()
        super(PaymentTermsMixIn, self).clean()
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        if self.is_draft():
            self.amount_paid = Decimal('0.00')
            self.paid = False
            self.paid_date = None
            self.progress = 0


class InvoiceModel(InvoiceModelAbstract):
    """
    Base Invoice Model from Abstract.
    """


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=invoicemodel_predelete, sender=InvoiceModel)
