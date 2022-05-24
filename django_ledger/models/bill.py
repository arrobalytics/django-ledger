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
from typing import Union
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count
from django.db.models.signals import post_delete
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel
from django_ledger.models import LazyLoader
from django_ledger.models.mixins import CreateUpdateMixIn, LedgerWrapperMixIn, MarkdownNotesMixIn

lazy_loader = LazyLoader()

BILL_NUMBER_CHARS = ascii_uppercase + digits


def generate_bill_number(length: int = 10, prefix: bool = True) -> str:
    """
    A function that generates a random bill identifier for new bill models.
    :param prefix:
    :param length: The length of the bill number.
    :return: A string representing a random bill identifier.
    """
    bill_number = ''.join(choices(BILL_NUMBER_CHARS, k=length))
    if prefix:
        bill_number = 'B-' + bill_number
    return bill_number


class BillModelQuerySet(models.QuerySet):

    def paid(self):
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_PAID)

    def approved(self):
        return self.filter(bill_status__exact=BillModel.BILL_STATUS_APPROVED)


class BillModelManager(models.Manager):

    def get_queryset(self):
        return BillModelQuerySet(self.model, using=self._db)

    def for_user(self, user_model):
        return self.get_queryset().filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model):
        if isinstance(entity_slug, EntityModel):
            return self.get_queryset().filter(
                Q(ledger__entity=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )
        elif isinstance(entity_slug, str):
            return self.get_queryset().filter(
                Q(ledger__entity__slug__exact=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )

    def for_entity_unpaid(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug,
                             user_model=user_model)
        return qs.approved()


class BillModelAbstract(LedgerWrapperMixIn,
                        MarkdownNotesMixIn,
                        CreateUpdateMixIn):
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
    bill_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Bill Number'))
    bill_status = models.CharField(max_length=10, choices=BILL_STATUS, default=BILL_STATUS[0][0],
                                   verbose_name=_('Bill Status'))
    xref = models.SlugField(null=True, blank=True, verbose_name=_('External Reference Number'))
    vendor = models.ForeignKey('django_ledger.VendorModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor'))
    additional_info = models.JSONField(blank=True,
                                       null=True,
                                       verbose_name=_('Bill Additional Info'))
    bill_items = models.ManyToManyField('django_ledger.ItemModel',
                                        through='django_ledger.ItemThroughModel',
                                        through_fields=('bill_model', 'item_model'),
                                        verbose_name=_('Bill Items'))

    in_review_date = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    approved_date = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    paid_date = models.DateField(null=True, blank=True, verbose_name=_('Paid Date'))
    void_date = models.DateField(null=True, blank=True, verbose_name=_('Void Date'))
    canceled_date = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

    objects = BillModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Bill')
        verbose_name_plural = _('Bills')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['bill_status']),
            models.Index(fields=['terms']),
            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),
        ]

    def __str__(self):
        return f'Bill: {self.bill_number}'

    # Configuration...
    def configure(self,
                  entity_slug: Union[str, EntityModel],
                  user_model,
                  ledger_posted: bool = False,
                  bill_desc: str = None):

        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        if not self.bill_number:
            self.bill_number = generate_bill_number()
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
        return ledger_model, self

    # State..
    def get_migrate_state_desc(self):
        """
        Must be implemented.
        :return:
        """
        return f'Bill {self.bill_number} account adjustment.'

    def get_itemthrough_data(self, queryset=None) -> tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.select_related(
                'item_model', 'po_model', 'bill_model').all()
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )

    def get_item_data(self, entity_slug, queryset=None):
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all()
            queryset = queryset.filter(bill_model__ledger__entity__slug__exact=entity_slug)
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

    def update_amount_due(self, queryset=None, item_list: list = None) -> None or tuple:
        if item_list:
            # self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            self.amount_due = round(sum(a.total_amount for a in item_list), 2)
            return
        queryset, item_data = self.get_itemthrough_data(queryset=queryset)
        self.amount_due = round(item_data['amount_due'], 2)
        return queryset, item_data

    # State
    def is_draft(self):
        return self.bill_status == self.BILL_STATUS_DRAFT

    def is_review(self):
        return self.bill_status == self.BILL_STATUS_REVIEW

    def is_approved(self):
        return self.bill_status == self.BILL_STATUS_APPROVED

    def is_paid(self):
        return self.bill_status == self.BILL_STATUS_PAID

    def is_canceled(self):
        return self.bill_status == self.BILL_STATUS_CANCELED

    def is_void(self):
        # todo: use VOID status instead
        return self.bill_status == self.BILL_STATUS_VOID

    # Permissions....
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

    def can_delete(self):
        return any([
            self.is_review(),
            self.is_draft()
        ])

    def can_void(self):
        return self.is_approved()

    def can_cancel(self):
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self):
        return self.is_draft()

    def can_migrate(self) -> bool:
        if not self.is_approved():
            return False
        return super(BillModelAbstract, self).can_migrate()

    # --> ACTIONS <---
    def mark_as_draft(self, commit: bool = False, **kwargs):
        if not self.can_draft():
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as draft. Must be In Review.'
            )
        self.bill_status = self.BILL_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'bill_status',
                    'updated'
                ]
            )

    def get_mark_as_draft_html_id(self):
        return f'djl-{self.uuid}-mark-as-draft'

    def get_mark_as_draft_url(self):
        return reverse('django_ledger:bill-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        return _('Do you want to mark Bill %s as Draft?') % self.bill_number

    # IN REVIEW ACTIONS....
    def mark_as_review(self, commit: bool = False, **kwargs):
        if not self.can_review():
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as in review. Must be Draft and Configured.'
            )
        if not self.amount_due:
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as in review. Amount due must be greater than 0.'
            )

        self.bill_status = self.BILL_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'bill_status',
                    'updated'
                ]
            )

    def get_mark_as_review_html_id(self):
        return f'djl-{self.uuid}-mark-as-review'

    def get_mark_as_review_url(self):
        return reverse('django_ledger:bill-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        return _('Do you want to mark Bill %s as In Review?') % self.bill_number

    # APPROVED ACTIONS....
    def mark_as_approved(self,
                         entity_slug,
                         user_model,
                         approved_date: date,
                         commit: bool = False,
                         **kwargs):
        if not self.can_approve():
            raise ValidationError(
                f'Bill {self.bill_number} cannot be marked as in approved.'
            )
        self.amount_paid = self.amount_due
        self.bill_status = self.BILL_STATUS_APPROVED

        self.date = localdate() if not approved_date else approved_date
        self.new_state(commit=True)
        self.clean()
        if commit:
            self.migrate_state(
                entity_slug=entity_slug,
                user_model=user_model,
                je_date=approved_date,
            )
            self.ledger.post(commit=commit)
            self.save(update_fields=[
                'bill_status',
                'updated'
            ])

    def get_mark_as_approved_html_id(self):
        return f'djl-{self.uuid}-mark-as-approved'

    def get_mark_as_approved_url(self):
        return reverse('django_ledger:bill-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        return _('Do you want to mark Bill %s as Approved?') % self.bill_number

    # DELETE ACTIONS...
    def mark_as_delete(self, **kwargs):
        if not self.can_delete():
            raise ValidationError(f'Bill {self.bill_number} cannot be deleted. Must be void after Approved.')
        self.delete(**kwargs)

    def get_mark_as_delete_html_id(self):
        return f'djl-{self.uuid}-void'

    def get_mark_as_delete_url(self):
        return reverse('django_ledger:bill-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_delete_message(self):
        return _('Do you want to void Bill %s?') % self.bill_number

    # PAY ACTIONS....
    def mark_as_paid(self,
                     user_model,
                     entity_slug: str,
                     paid_date: date = None,
                     itemthrough_queryset=None,
                     commit: bool = False,
                     **kwargs):
        if not self.can_pay():
            raise ValidationError(f'Cannot mark Bill {self.bill_number} as paid...')

        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        self.paid_date = localdate() if not paid_date else paid_date

        if self.paid_date > localdate():
            raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        if self.paid_date < self.date:
            raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
                                  f' date {self.date}.')

        self.bill_status = self.BILL_STATUS_PAID
        self.new_state(commit=True)
        self.clean()

        if not itemthrough_queryset:
            itemthrough_queryset = self.itemthroughmodel_set.all()

        if commit:
            self.save(update_fields=[
                'paid_date',
                'progress',
                'amount_paid',
                'bill_status',
                'updated'
            ])
            ItemThroughModel = lazy_loader.get_item_through_model()
            # update this field only if there's a PO assigned
            itemthrough_queryset.update(po_item_status=ItemThroughModel.STATUS_ORDERED)
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug,
                itemthrough_queryset=itemthrough_queryset,
                je_date=paid_date,
                force_migrate=True
            )
            self.lock_ledger(commit=True)

    def get_mark_as_paid_html_id(self):
        return f'djl-{self.uuid}-mark-as-approved'

    def get_mark_as_paid_url(self):
        return reverse('django_ledger:bill-action-mark-as-paid',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_paid_message(self):
        return _('Do you want to mark Bill %s as Paid?') % self.bill_number

    # VOID Actions...

    def mark_as_void(self, user_model, entity_slug, void_date: date = None, commit: bool = False, **kwargs):
        if not self.can_void():
            raise ValidationError(f'Bill {self.bill_number} cannot be voided. Must be approved.')

        self.void_date = void_date if void_date else localdate()
        self.bill_status = self.BILL_STATUS_VOID
        self.void_state(commit=True)
        self.clean()

        if commit:
            self.unlock_ledger(commit=True, raise_exception=False)
            self.migrate_state(
                entity_slug=entity_slug,
                user_model=user_model,
                void=True,
                void_date=self.void_date,
                force_migrate=True)
            self.save()
            self.lock_ledger(commit=True, raise_exception=False)

    def get_mark_as_void_html_id(self):
        return f'djl-{self.uuid}-delete'

    def get_mark_as_void_url(self):
        return reverse('django_ledger:bill-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        return _('Do you want to void Bill %s?') % self.bill_number

    # Cancel Actions...
    def mark_as_canceled(self, canceled_date: date,  commit: bool = False, **kwargs):
        if not self.can_cancel():
            raise ValidationError(f'Bill {self.bill_number} cannot be canceled. Must be draft or in review.')

        self.canceled_date = localdate() if not canceled_date else canceled_date
        self.bill_status = self.BILL_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'bill_status',
                'canceled_date'
            ])

        # self.void_date = void_date if void_date else localdate()
        # self.bill_status = self.BILL_STATUS_VOID
        # self.void_state(commit=True)
        # self.clean()
        #
        # if commit:
        #     self.unlock_ledger(commit=True, raise_exception=False)
        #     self.migrate_state(
        #         entity_slug=entity_slug,
        #         user_model=user_model,
        #         void=True,
        #         void_date=self.void_date,
        #         force_migrate=True)
        #     self.save()
        #     self.lock_ledger(commit=True, raise_exception=False)

    def get_mark_as_canceled_html_id(self):
        return f'djl-{self.uuid}-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        return reverse('django_ledger:bill-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        return _('Do you want to void as Canceled %s?') % self.bill_number

    # HTML Tags...
    def get_document_id(self):
        return self.bill_number

    def get_html_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_html_amount_due_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}-amount-due'

    def get_html_amount_paid_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}-amount-paid'

    def get_html_form_name(self):
        return f'djl-form-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_mark_paid_url(self, entity_slug):
        return reverse('django_ledger:bill-action-mark-as-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def clean(self):
        if not self.bill_number:
            self.bill_number = generate_bill_number()

        if self.is_draft():
            self.amount_paid = Decimal('0.00')
            self.paid = False
            self.paid_date = None
            self.progress = 0

        if not self.additional_info:
            self.additional_info = dict()

        super().clean()


class BillModel(BillModelAbstract):
    """
    Base Bill Model from Abstract.
    """


def billmodel_predelete(instance: BillModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=billmodel_predelete, sender=BillModel)
