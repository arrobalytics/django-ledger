"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count
from django.db.models.signals import post_delete
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn, AccruableItemMixIn
from django_ledger.models import LazyLoader

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


class BillModelManager(models.Manager):

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
        return qs.filter(paid=False)


class BillModelAbstract(AccruableItemMixIn, CreateUpdateMixIn):
    REL_NAME_PREFIX = 'bill'
    IS_DEBIT_BALANCE = False
    ALLOW_MIGRATE = True

    # todo: implement Void Bill (& Invoice)....
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    bill_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Bill Number'))
    xref = models.SlugField(null=True, blank=True, verbose_name=_('External Reference Number'))
    vendor = models.ForeignKey('django_ledger.VendorModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor'))
    additional_info = models.JSONField(default=dict, verbose_name=_('Bill Additional Info'))
    bill_items = models.ManyToManyField('django_ledger.ItemModel',
                                        through='django_ledger.ItemThroughModel',
                                        through_fields=('bill_model', 'item_model'),
                                        verbose_name=_('Bill Items'))

    objects = BillModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Bill')
        verbose_name_plural = _('Bills')
        indexes = [
            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),
            models.Index(fields=['date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['paid']),
        ]

    def __str__(self):
        return f'Bill: {self.bill_number}'

    def configure(self,
                  entity_slug: str or EntityModel,
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
        return ledger_model, self

    def get_absolute_url(self):
        return reverse('django_ledger:invoice-detail',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'invoice_pk': self.uuid
                       })

    def get_migrate_state_desc(self):
        """
        Must be implemented.
        :return:
        """
        return f'Bill {self.bill_number} account adjustment.'

    def get_document_id(self):
        return self.bill_number

    def get_html_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_html_form_name(self):
        return f'djl-form-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_mark_paid_url(self, entity_slug):
        return reverse('django_ledger:bill-mark-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': self.uuid
                       })

    def get_bill_item_data(self, queryset=None) -> tuple:
        if not queryset:
            queryset = self.itemthroughmodel_set.all()
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )

    def get_item_data(self, entity_slug, queryset=None):
        if not queryset:
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
            self.amount_due = sum(a.total_amount for a in item_list)
            return
        queryset, item_data = self.get_bill_item_data(queryset=queryset)
        self.amount_due = item_data['amount_due']
        return queryset, item_data

    def clean(self):
        if not self.bill_number:
            self.bill_number = generate_bill_number()
        super().clean()


class BillModel(BillModelAbstract):
    """
    Base Bill Model from Abstract.
    """


def billmodel_predelete(instance: BillModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=billmodel_predelete, sender=BillModel)
