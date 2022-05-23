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
from django_ledger.models.mixins import CreateUpdateMixIn, LedgerWrapperMixIn, MarkdownNotesMixIn

UserModel = get_user_model()

lazy_loader = LazyLoader()

INVOICE_NUMBER_CHARS = ascii_uppercase + digits


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

    def paid(self):
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_PAID)

    def approved(self):
        return self.filter(invoice_status__exact=InvoiceModel.INVOICE_STATUS_APPROVED)


class InvoiceModelManager(models.Manager):

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
                           MarkdownNotesMixIn,
                           CreateUpdateMixIn):
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
                                           through='django_ledger.ItemThroughModel',
                                           through_fields=('invoice_model', 'item_model'),
                                           verbose_name=_('Invoice Items'))

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['invoice_status']),
            models.Index(fields=['terms']),
            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),
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
        return any([
            self.is_approved()
        ])

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

    # ACTIONS...

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
    def mark_as_review(self, commit: bool = False, **kwargs):
        if not self.can_review():
            raise ValidationError(f'Cannot mark PO {self.uuid} as In Review...')
        if not self.amount_due:
            raise ValidationError(
                f'PO {self.invoice_number} cannot be marked as in review. Amount due must be greater than 0.'
            )
        self.invoice_status = self.INVOICE_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
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
    def mark_as_approved(self, commit: bool = False, **kwargs):
        if not self.can_approve():
            raise ValidationError(f'Cannot mark PO {self.uuid} as Approved...')
        self.invoice_status = self.INVOICE_STATUS_APPROVED
        self.clean()
        if commit:
            self.ledger.post(commit=True)
            self.save(update_fields=[
                'invoice_status',
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
                     paid_date: date = None,
                     commit: bool = False,
                     **kwargs):
        if not self.can_pay():
            raise ValidationError(f'Cannot mark PO {self.uuid} as Paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        self.paid_date = localdate() if not paid_date else paid_date

        if self.paid_date > localdate():
            raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        if self.paid_date < self.date:
            raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
                                  f' date {self.date}.')

        self.new_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_PAID
        self.clean()

        if commit:
            self.save(update_fields=[
                'paid_date',
                'progress',
                'amount_paid',
                'invoice_status',
                'updated'
            ])
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                force_migrate=True,
                je_date=paid_date
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
                     void_date: date = None,
                     commit: bool = False,
                     **kwargs):

        if not self.can_void():
            raise ValidationError(f'Cannot mark PO {self.uuid} as Void...')

        self.void_date = localdate() if not void_date else void_date
        self.void_state(commit=True)
        self.invoice_status = self.INVOICE_STATUS_VOID
        self.clean()

        # todo: add custom logic for void date...
        # if self.paid_date > localdate():
        #     raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        # if self.paid_date < self.date:
        #     raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
        #                           f' date {self.date}.')

        if commit:
            self.unlock_ledger(commit=True, raise_exception=False)
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                void=True,
                void_date=self.void_date,
                force_migrate=True
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
    def mark_as_canceled(self, commit: bool = False, **kwargs):
        if not self.can_cancel():
            raise ValidationError(f'Cannot cancel Invoice {self.invoice_number}.')

        self.invoice_status = self.INVOICE_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'invoice_status',
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

    def get_invoice_item_data(self, queryset=None) -> tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all().select_related('item_model')
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )

    def can_migrate(self) -> bool:
        return self.is_approved()

    def get_item_data(self, entity_slug: str, queryset=None):
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all()
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

    def update_amount_due(self, queryset=None, item_list: list = None) -> None or tuple:
        if item_list:
            # self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            self.amount_due = round(sum(a.total_amount for a in item_list), 2)
            return
        queryset, item_data = self.get_invoice_item_data(queryset=queryset)
        self.amount_due = round(item_data['amount_due'], 2)
        return queryset, item_data

    # def mark_as_paid(self,
    #                  user_model,
    #                  entity_slug: str,
    #                  paid_date: date = None,
    #                  itemthrough_queryset=None,
    #                  commit: bool = False):
    #
    #     self.paid = True
    #     self.progress = Decimal.from_float(1.0)
    #     self.amount_paid = self.amount_due
    #     paid_dt = localdate() if not paid_date else paid_date
    #
    #     if not self.paid_date:
    #         self.paid_date = paid_dt
    #     if self.paid_date > paid_dt:
    #         raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
    #     if self.paid_date < self.date:
    #         raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
    #                               f' date {self.date}.')
    #     self.update_state()
    #     self.clean()
    #     if commit:
    #         self.migrate_state(
    #             user_model=user_model,
    #             entity_slug=entity_slug,
    #             itemthrough_queryset=itemthrough_queryset
    #         )
    #         ledger_model = self.ledger
    #         ledger_model.locked = True
    #         # pylint: disable=no-member
    #         ledger_model.save(update_fields=['locked', 'updated'])
    #         self.save()

    def clean(self):
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        if self.is_draft():
            self.amount_paid = Decimal('0.00')
            self.paid = False
            self.paid_date = None
            self.progress = 0
        super().clean()


class InvoiceModel(InvoiceModelAbstract):
    """
    Base Invoice Model from Abstract.
    """


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=invoicemodel_predelete, sender=InvoiceModel)
