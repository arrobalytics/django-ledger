"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <ptulshyan77@gmail.com>
"""

from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn, TaxCollectionMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX

"""
The model for managing the details of the Customers.
For raising an Invoice ,we have to select the Customer Name. 
In case, the customer is not created , then the same needs to be created under this table.

"""


class CustomerModelQueryset(models.QuerySet):
    pass


class CustomerModelManager(models.Manager):
    """
    A custom defined Customer  Model Manager that will act as an inteface to handling the DB queries to the Customer Model.
    The default "get_queryset" has been used"

    """

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            Q(active=True) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


class CustomerModelAbstract(ContactInfoMixIn, TaxCollectionMixIn, CreateUpdateMixIn):
    """
    This is the main class which the Customer Model database will inherit, and it contains the fields/columns/attributes which the said table will have.
    In addition to the attributes mentioned below, it also has the fields/columns/attributes mentioned in below MixIn:
    
    ContactinfoMixIn
    CreateUpdateMixIn
    
    Read about these mixin here.

    Below are the fields specific to the bill model.
    @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the unique uuid generated.
    @entity: This is a slug  Field and hence a random bill number with Max Length of 20 will be defined
    @description: A text field to capture the decsription about the customer
    @active: We can set any customer code to be active or Incative. By default, whenever a new Cutsomer code is craeted , the same is set to True i.e "Active"
    @hidden: We can set any customer code to be hidden. By default, whenever a new Cutsomer code is craeted , the same is set to False i.e "not Hidden"
    @aditinal_info: Any additional infor about the customer
    @objects:setting the default Model Manager to the CustomerModelManagers

    Some Meta Information: (Additional data points regarding this model that may alter its behavior)

    @verbose_name: A human-readable name for this Model (Also translatable to other languages with django translation> gettext_lazy)
    @unique_together: the concatenation of entity  & customer code would remain unique throughout the model i.e database
    @indexes : Index created on different attributes for better db & search queries

    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=30, editable=False, verbose_name=_('Customer Number'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Customer Entity'))
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)

    additional_info = models.JSONField(null=True, blank=True)

    objects = CustomerModelManager.from_queryset(queryset_class=CustomerModelQueryset)()

    class Meta:
        abstract = True
        verbose_name = _('Customer')
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
            models.Index(fields=['customer_number']),
        ]
        unique_together = [
            ('entity', 'customer_number')
        ]

    def __str__(self):
        return f'Customer: {self.customer_name}'

    def can_generate_customer_number(self) -> bool:
        return all([
            self.entity_id,
            not self.customer_number
        ])

    def _get_next_state_model(self, raise_exception: bool = True):
        EntityStateModel = lazy_loader.get_entity_state_model()

        try:
            LOOKUP = {
                'entity_id__exact': self.entity_id,
                'key__exact': EntityStateModel.KEY_CUSTOMER
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()

            return state_model
        except ObjectDoesNotExist:

            LOOKUP = {
                'entity_id': self.entity_id,
                'entity_unit_id': None,
                'fiscal_year': None,
                'key': EntityStateModel.KEY_CUSTOMER,
                'sequence': 1
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_customer_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Customer Number available.
        @param commit: Commit transaction into CustomerModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
        """
        if self.can_generate_customer_number():
            with transaction.atomic(durable=True):

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.customer_number = f'{DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX}-{seq}'

            if commit:
                self.save(update_fields=['customer_number', 'updated'])

        return self.customer_number

    def clean(self):
        if not self.customer_number:
            self.generate_customer_number(commit=False)

    def save(self, **kwargs):
        if not self.customer_number:
            self.generate_customer_number(commit=False)
        super(CustomerModelAbstract, self).save(**kwargs)


class CustomerModel(CustomerModelAbstract):
    """
    Base Customer Model Implementation
    """
