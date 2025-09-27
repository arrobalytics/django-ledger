from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models import F, Manager, Q, QuerySet
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import IOMixIn
from django_ledger.models import (
    AccountModel,
    CreateUpdateMixIn,
    CustomerModel,
    EntityModel,
    EntityStateModel,
    EntityUnitModel,
    MarkdownNotesMixIn,
    VendorModel,
)
from django_ledger.settings import (
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX,
)


class ReceiptModelValidationError(ValidationError):
    pass


class ReceiptModelQuerySet(QuerySet):
    def for_user(self, user_model) -> 'ReceiptModelQuerySet':
        return self.filter(
            Q(ledger_model__entity__admin=user_model)
            | Q(ledger_model__entity__managers__in=[user_model])
        )

    def for_dates(self, from_date, to_date) -> 'ReceiptModelQuerySet':
        return self.filter(receipt_date__gte=from_date, receipt_date__lte=to_date)

    def for_vendor(
        self, vendor_model: VendorModel | str | UUID
    ) -> 'ReceiptModelQuerySet':
        if isinstance(vendor_model, str):
            return self.filter(
                vendor_model__vendor_number__iexact=vendor_model,
                customer_model__isnull=True,
            )
        elif isinstance(vendor_model, VendorModel):
            return self.filter(
                vendor_model=vendor_model,
                customer_model__isnull=True,
            )
        elif isinstance(vendor_model, UUID):
            return self.filter(
                vendor_model_id=vendor_model,
                customer_model__isnull=True,
            )
        raise ReceiptModelValidationError(
            'Invalid Vendor Model: {}, must be instance of VendorModel, UUID, str'.format(
                vendor_model
            )
        )

    def for_customer(
        self, customer_model: CustomerModel | str | UUID
    ) -> 'ReceiptModelQuerySet':
        if isinstance(customer_model, str):
            return self.filter(
                customer_model__customer_number__iexact=customer_model,
                vendor_model__isnull=True,
            )
        elif isinstance(customer_model, CustomerModel):
            return self.filter(
                customer_model=customer_model,
                vendor_model__isnull=True,
            )
        elif isinstance(customer_model, UUID):
            return self.filter(
                customer_model_id=customer_model,
                vendor_model__isnull=True,
            )
        raise ReceiptModelValidationError(
            'Invalid Customer Model: {}, must be instance of CustomerModel, UUID, str'.format(
                customer_model
            )
        )


class ReceiptModelManager(Manager):
    def get_queryset(self):
        return (
            ReceiptModelQuerySet(self.model, using=self._db)
            .select_related('ledger_model')
            .annotate(
                _entity_uuid=F('ledger_model__entity__uuid'),
                _entity_slug=F('ledger_model__entity__slug'),
                _last_closing_date=F('ledger_model__entity__last_closing_date'),
            )
        )

    def for_entity(
        self, entity_model: EntityModel | str | UUID
    ) -> ReceiptModelQuerySet:
        qs = self.get_queryset()
        if isinstance(entity_model, str):
            qs = qs.filter(ledger_model__entity__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(ledger_model__entity_id=entity_model)
        elif isinstance(entity_model, EntityModel):
            qs = qs.filter(ledger_model__entity=entity_model)
        else:
            raise ReceiptModelValidationError(
                f'Must pass either EntityModel, string or UUID, not {type(entity_model)}.'
            )
        return qs


class ReceiptModelAbstract(CreateUpdateMixIn, MarkdownNotesMixIn, IOMixIn):
    SALES_RECEIPT = 'sales'
    SALES_REFUND = 'customer_refund'
    EXPENSE_RECEIPT = 'expense'
    EXPENSE_REFUND = 'expense_refund'
    TRANSFER_RECEIPT = 'transfer'

    RECEIPT_TYPES = [
        (SALES_RECEIPT, 'Sales Receipt'),
        (SALES_REFUND, 'Sales Refund'),
        (EXPENSE_RECEIPT, 'Expense Receipt'),
        (EXPENSE_REFUND, 'Expense Refund'),
        (TRANSFER_RECEIPT, 'Transfer Receipt'),
    ]
    RECEIPT_TYPES_MAP = dict(RECEIPT_TYPES)

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    receipt_number = models.CharField(_('Receipt Number'), max_length=255)
    receipt_date = models.DateField(_('Receipt Date'))
    receipt_type = models.CharField(
        choices=RECEIPT_TYPES, verbose_name=_('Receipt Type')
    )

    ledger_model = models.ForeignKey(
        'django_ledger.LedgerModel',
        on_delete=models.PROTECT,
        verbose_name=_('Ledger Model'),
        editable=False,
    )

    unit_model = models.ForeignKey(
        'django_ledger.EntityUnitModel',
        on_delete=models.PROTECT,
        verbose_name=_('Unit Model'),
        help_text=_(
            'Helps segregate receipts and transactions into different classes or departments.'
        ),
        null=True,
        blank=True,
    )

    customer_model = models.ForeignKey(
        'django_ledger.CustomerModel',
        on_delete=models.PROTECT,
        verbose_name=_('Customer Model'),
        null=True,
        blank=True,
    )
    vendor_model = models.ForeignKey(
        'django_ledger.VendorModel',
        on_delete=models.PROTECT,
        verbose_name=_('Vendor Model'),
        null=True,
        blank=True,
    )

    charge_account = models.ForeignKey(
        'django_ledger.AccountModel',
        on_delete=models.PROTECT,
        verbose_name=_('Charge Account'),
        help_text=_(
            'The financial account (cash or credit) where this transaction was made.'
        ),
        related_name='charge_receiptmodel_set',
    )

    receipt_account = models.ForeignKey(
        'django_ledger.AccountModel',
        on_delete=models.PROTECT,
        verbose_name=_('PnL Account'),
        help_text=_(
            'The income or expense account where this transaction will be reflected'
        ),
    )

    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        verbose_name=_('Receipt Amount'),
        help_text=_('Amount of the receipt.'),
        validators=[MinValueValidator(0)],
    )

    staged_transaction_model = models.OneToOneField(
        'django_ledger.StagedTransactionModel',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name=_('Staged Transaction Model'),
        help_text=_(
            'The staged transaction associated with the receipt from bank feeds.'
        ),
    )

    objects = ReceiptModelManager.from_queryset(queryset_class=ReceiptModelQuerySet)()

    class Meta:
        abstract = True
        verbose_name = _('Sales/Expense Receipt')
        verbose_name_plural = _('Sales/Expense Receipts')
        indexes = [
            models.Index(fields=['receipt_number']),
            models.Index(fields=['ledger_model']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['receipt_type']),
            models.Index(fields=['customer_model']),
            models.Index(fields=['vendor_model']),
        ]

    @property
    def entity_slug(self) -> str:
        try:
            return getattr(self, '_entity_slug')
        except AttributeError:
            pass
        return self.ledger_model.entity_slug

    @property
    def entity_uuid(self) -> UUID:
        try:
            return getattr(self, '_entity_uuid')
        except AttributeError:
            pass
        return self.ledger_model.entity_uuid

    @property
    def ledger_posted(self):
        return self.ledger_model.is_posted()

    @property
    def posted(self):
        return self.ledger_model.is_posted()

    @property
    def last_closing_date(self):
        try:
            return getattr(self, '_last_closing_date')
        except AttributeError:
            pass
        return self.ledger_model.entity.last_closing_date

    # Actions
    def can_delete(self) -> bool:
        return all(
            [
                self.last_closing_date < self.receipt_date,
            ]
        )

    def delete(
        self, using=None, keep_parents=False, delete_ledger: bool = True, **kwargs
    ):
        if not self.can_delete():
            raise ReceiptModelValidationError(
                message=_(
                    'Receipt cannot be deleted because it falls within a closed period.'
                ),
            )
        ledger = self.ledger_model
        with transaction.atomic():
            if ledger.is_locked():
                ledger.unlock(commit=True, raise_exception=True)

            ledger.journal_entries.all().delete()

            return super().delete(using=using, keep_parents=keep_parents)

    def is_sales_receipt(self) -> bool:
        return any(
            [
                self.receipt_type == self.SALES_RECEIPT,
                self.receipt_type == self.SALES_REFUND,
            ]
        )

    def is_expense_receipt(self) -> bool:
        return any(
            [
                self.receipt_type == self.EXPENSE_RECEIPT,
                self.receipt_type == self.EXPENSE_REFUND,
            ]
        )

    def is_transfer_receipt(self) -> bool:
        return self.receipt_type == self.TRANSFER_RECEIPT

    def get_receipt_type_for_amount(self, amount: float | int | Decimal) -> str:
        """
        Determines the proper receipt_type based on whether the receipt is tied to
        a customer or a vendor and the sign of the amount.

        Rules:
        - Customer:
            amount >= 0 -> SALES_RECEIPT
            amount < 0  -> CUSTOMER_REFUND
        - Vendor:
            amount <= 0 -> EXPENSE_RECEIPT
            amount > 0  -> EXPENSE_REFUND

        Raises:
            ReceiptModelValidationError if both customer and vendor are set,
            or if neither is set.
        """
        if self.customer_model_id and self.vendor_model_id:
            raise ReceiptModelValidationError(
                message='Cannot determine receipt type when both customer and vendor are set.'
            )

        if self.customer_model_id:
            return self.SALES_RECEIPT if float(amount) >= 0 else self.SALES_REFUND

        if self.vendor_model_id:
            return self.EXPENSE_REFUND if float(amount) > 0 else self.EXPENSE_RECEIPT

        raise ReceiptModelValidationError(
            message='Cannot determine receipt type without a customer or vendor.'
        )

    def is_configured(self) -> bool:
        return all(
            [
                self.receipt_date is not None,
                self.receipt_type is not None,
                self.ledger_model_id is not None,
            ]
        )

    def can_generate_receipt_number(self) -> bool:
        return all([not self.receipt_number])

    def _get_next_state_model(self, raise_exception: bool = True):
        entity_model = self.ledger_model.entity
        fy_key = entity_model.get_fy_for_date(dt=self.receipt_date)

        LOOKUP = {
            'entity_model_id__exact': entity_model.uuid,
            'entity_unit_id__exact': None,
            'fiscal_year': fy_key,
            'key__exact': EntityStateModel.KEY_RECEIPT,
        }

        try:
            state_model_qs = (
                EntityStateModel.objects.filter(**LOOKUP)
                .select_related('entity_model')
                .select_for_update()
            )

            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save(update_fields=['sequence'])
            state_model.refresh_from_db()
            return state_model
        except ObjectDoesNotExist:
            LOOKUP = {
                'entity_model_id': entity_model.uuid,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key': EntityStateModel.KEY_RECEIPT,
                'sequence': 1,
            }

            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_receipt_number(self, commit: bool = False) -> str:
        if self.can_generate_receipt_number():
            state_model = None
            while not state_model:
                state_model = self._get_next_state_model(raise_exception=False)

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.receipt_number = (
                f'{DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'
            )

            if commit:
                self.save(update_fields=['receipt_number', 'updated'])

        return self.receipt_number

    def configure(
        self,
        entity_model: EntityModel | str | UUID,
        receipt_type: Literal[
            SALES_RECEIPT, SALES_REFUND, EXPENSE_RECEIPT, EXPENSE_REFUND
        ],
        amount: int | float | Decimal,
        unit_model: Optional[EntityUnitModel | str | UUID] = None,
        receipt_date: Optional[datetime | str] = None,
        vendor_model: Optional[VendorModel | str | UUID] = None,
        customer_model: Optional[CustomerModel | str | UUID] = None,
        charge_account: Optional[AccountModel] = None,
        receipt_account: Optional[AccountModel] = None,
        staged_transaction_model=None,
        commit: bool = True,
    ):
        if not self.is_configured():
            with transaction.atomic():
                if amount < 0:
                    raise ReceiptModelValidationError(
                        message='Receipt amount must be greater than zero'
                    )
                if isinstance(entity_model, EntityModel):
                    pass
                elif isinstance(entity_model, UUID):
                    entity_model = EntityModel.objects.get(uuid__exact=entity_model)
                elif isinstance(entity_model, str):
                    entity_model = EntityModel.objects.get(slug__exact=entity_model)

                if all([vendor_model, customer_model]):
                    raise ReceiptModelValidationError(
                        message='Must pass VendorModel or CustomerModel, not both.',
                    )

                if not any([vendor_model, customer_model]):
                    raise ReceiptModelValidationError(
                        message='Must pass VendorModel or CustomerModel.',
                    )

                # checks if a vendor model has been previously assigned....
                if all(
                    [
                        vendor_model is not None,
                        self.vendor_model_id is not None,
                    ]
                ):
                    raise ReceiptModelValidationError(
                        message='Vendor Model already set.'
                    )

                # checks if a customer model has been previously assigned....
                if all(
                    [
                        customer_model is not None,
                        self.customer_model_id is not None,
                    ]
                ):
                    raise ReceiptModelValidationError(
                        message='Customer Model already set.'
                    )

                # get vendor model...
                if vendor_model:
                    if isinstance(vendor_model, str):
                        vendor_model = VendorModel.objects.for_entity(
                            entity_model=entity_model
                        ).get(vendor_number__iexact=vendor_model)
                    elif isinstance(customer_model, UUID):
                        vendor_model = VendorModel.objects.for_entity(
                            entity_model=entity_model
                        ).get(uuid__exact=vendor_model)
                    elif isinstance(vendor_model, VendorModel):
                        vendor_model.validate_for_entity(entity_model=entity_model)
                    else:
                        raise ReceiptModelValidationError(
                            message='VendorModel must be either a VendorModel, UUID or Vendor Number.'
                        )
                    self.vendor_model = vendor_model

                # get customer model
                if customer_model:
                    if isinstance(customer_model, str):
                        customer_model = CustomerModel.objects.for_entity(
                            entity_model=customer_model
                        ).get(customer_number__iexact=customer_model)
                    elif isinstance(customer_model, UUID):
                        customer_model = CustomerModel.objects.for_entity(
                            entity_model=customer_model
                        ).get(uuid__exact=customer_model)
                    elif isinstance(customer_model, CustomerModel):
                        customer_model.validate_for_entity(entity_model=entity_model)
                    else:
                        raise ReceiptModelValidationError(
                            message='Customer Model must be either a CustomerModel, UUID or Customer Number.'
                        )
                    self.customer_model = customer_model

                if unit_model:
                    if isinstance(unit_model, str):
                        unit_model = EntityUnitModel.objects.for_entity(
                            entity_model=entity_model
                        ).get(slug__exact=unit_model)
                    elif isinstance(unit_model, UUID):
                        unit_model = EntityUnitModel.objects.for_entity(
                            entity_model=entity_model
                        ).get(uuid__exact=unit_model)
                    elif isinstance(unit_model, EntityUnitModel):
                        unit_model.validate_for_entity(entity_model=entity_model)

                self.receipt_type = receipt_type
                self.amount = amount
                self.receipt_date = localdate() if not receipt_date else receipt_date
                self.charge_account = charge_account
                self.receipt_account = receipt_account
                self.unit_model = unit_model
                self.staged_transaction_model = staged_transaction_model

                self.ledger_model = entity_model.create_ledger(
                    name=entity_model.name,
                    posted=True,
                    commit=False,
                )
                receipt_number = self.generate_receipt_number(commit=True)
                self.ledger_model.name = receipt_number
                self.ledger_model.save()
                self.full_clean()

                if commit:
                    self.save()

    def can_migrate(self) -> bool:
        return all(
            [
                self.receipt_date is not None,
                any(
                    [
                        self.vendor_model_id is not None,
                        self.customer_model_id is not None,
                    ]
                ),
            ]
        )

    def migrate_receipt(self):
        if not self.is_configured():
            raise ReceiptModelValidationError(
                message='Receipt Model must be configured. Call configure() before migrating receipt.',
            )
        if not self.can_migrate():
            raise ReceiptModelValidationError(
                message='Must have VendorModel or CustomerModel, not both.',
            )

        commit_dict = self.staged_transaction_model.commit_dict(split_txs=False)
        ledger_model = self.ledger_model
        for je_data in commit_dict:
            _, _ = ledger_model.commit_txs(
                je_timestamp=self.receipt_date,
                je_unit_model=self.unit_model,
                je_posted=True,
                je_desc=f'Receipt Number: {self.receipt_number}',
                je_origin='migrate_receipt',
                je_txs=je_data,
            )
            staged_to_save = set(i['staged_tx_model'] for i in je_data)
            for i in staged_to_save:
                # todo: isn't the same staged txs forall txs?.. no need to save it multiple times...
                i.save(update_fields=['transaction_model', 'updated'])

    # URL helpers
    def get_absolute_url(self) -> str:
        return reverse(
            'django_ledger:receipt-detail',
            kwargs={'entity_slug': self.entity_slug, 'receipt_pk': self.uuid},
        )

    def get_list_url(self) -> str:
        return reverse(
            'django_ledger:receipt-list', kwargs={'entity_slug': self.entity_slug}
        )

    def get_delete_url(self) -> str:
        return reverse(
            'django_ledger:receipt-delete',
            kwargs={'entity_slug': self.entity_slug, 'receipt_pk': self.uuid},
        )

    def get_customer_list_url(self) -> Optional[str]:
        if not self.customer_model_id:
            return None
        return reverse(
            'django_ledger:receipt-list-customer',
            kwargs={
                'entity_slug': self.entity_slug,
                'customer_pk': self.customer_model_id,
            },
        )

    def get_vendor_list_url(self) -> Optional[str]:
        if not self.vendor_model_id:
            return None
        return reverse(
            'django_ledger:receipt-list-vendor',
            kwargs={'entity_slug': self.entity_slug, 'vendor_pk': self.vendor_model_id},
        )

    def get_customer_report_url(self) -> Optional[str]:
        if not self.customer_model_id:
            return None
        return reverse(
            'django_ledger:receipt-report-customer',
            kwargs={
                'entity_slug': self.entity_slug,
                'customer_pk': self.customer_model_id,
            },
        )

    def get_vendor_report_url(self) -> Optional[str]:
        if not self.vendor_model_id:
            return None
        return reverse(
            'django_ledger:receipt-report-vendor',
            kwargs={'entity_slug': self.entity_slug, 'vendor_pk': self.vendor_model_id},
        )

    def get_import_job_url(self) -> Optional[str]:
        if not self.staged_transaction_model_id:
            return None
        job = self.staged_transaction_model.import_job
        return reverse(
            'django_ledger:data-import-job-txs',
            kwargs={'entity_slug': self.entity_slug, 'job_pk': job.uuid},
        )

    def get_staged_tx_url(self) -> Optional[str]:
        if not self.staged_transaction_model_id:
            return None
        base = self.get_import_job_url()
        return f'{base}#staged-tx-{self.staged_transaction_model_id}' if base else None

    def clean(self):
        if self.is_sales_receipt():
            if not self.customer_model_id:
                raise ReceiptModelValidationError(
                    message=_('Sales receipt must have a customer model.')
                )
            self.vendor_model = None

        if self.is_expense_receipt():
            if not self.vendor_model_id:
                raise ReceiptModelValidationError(
                    message=_('Expense receipt must have a vendor model.')
                )
            self.customer_model = None


class ReceiptModel(ReceiptModelAbstract):
    class Meta:
        abstract = False


def receiptmodel_presave(instance: ReceiptModel, **kwargs):
    pass


pre_save.connect(receiptmodel_presave, sender=ReceiptModel)
