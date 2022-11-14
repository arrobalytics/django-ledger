"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <ptulshyan77@gmail.com>

"""


"""
Chart Of Account: This is a basically the entire collection of all the accounts that is present and a logical aggregation of those accounts.
The Chart of accounts is the backbone of making of any financial statements. Transactions are recorded into individual accounts based on their individual type.
The accounts which are of a similar nature will be grouped and classified accordingly.

For instance: We can have a heading as "Fixed Asssets" in the Balance Sheet, which will consists of Tangible, Intangible assets.

Further, the tangible assets will consists of multiple accounts like Building, Plant & Equipments, Machinery, Furnitures.
So, aggregation of balances of individual accounts based on the Chart of accounts , helps in prerapartion of the Financial Statements.


"""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Manager, Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn

UserModel = get_user_model()

"""
Firstly, we have set the UsermOdel as the user which is currently active.

The "code"used in this file refers to the account code that is uniquely assigned to any account Name.
This is similar to the GL code which we have under an SAP environment

The "coa_model" refers to the ChartofAccounts model that is separate for every entity.


"""


def get_coa_account(coa_model, code):

    """
    The function is used for filtering the particular account code from the list of all the codes in the Chart Of Accounts.
    In case the code doesnt eist, it will raise a non Existent error
    """



    try:
        qs = coa_model.acc_assignments.available()
        acc_model = qs.get(account__code__iexact=code)
        return acc_model
    except ObjectDoesNotExist:
        raise ValueError(
            'Account {acc} is either not assigned, inactive, locked or non existent for CoA: {coa}'.format(
                acc=code,
                coa=coa_model.__str__()
            ))


def make_account_active(coa_model, account_codes: str or list):

    """
    This function is used for making a single or a list of account_codes as "active".
    Whenever a new account is created under the "Accounts" Model, the said code is first set as Inactive.
    So, the below function actually make the code (list of codes) as "Active"


    """

    if isinstance(account_codes, str):
        account_codes = [account_codes]
    qs = coa_model.accounts.all()
    acc = qs.filter(code__in=account_codes)
    acc.update(active=True)


class ChartOfAccountModelManager(Manager):
    

    """
    This is the custome defined Model Manager whic will act as an nterface between the db queries and the ChartofAccountModel.
    This manager allows for db queries to pass through 2 filters . The "entity_slug" filter and the user filter.


    """

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__iexact=entity_slug) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    """
    Base Chart of Accounts Model Abstract

    This is the main abstract class which the ChartOfAccount Model database will inherit, and it contains the fields/columns/attributes which the said ledger table will have.
    In addition to the attributes mentioned below, it also has the the fields/columns/attributes mentioned below:
    
    1. SlugMixIn
    2.CreateUpdateMixIn
    
    Read about these mixin here.

    Below are the fields specific to the chart_of_accounts model.

    @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the unique uuid generated.
    @entity: This will be onetoOne Entity Mapping . Each ChartOf Accounts must be mapped to a Entity
    @locked:This determines whether any changes can be done in the account or not. Before making any update to the ChartOf Account , the account needs to be unlocked
    Default value is set to False i.e Unlocked
    @escription: This is the decription of the Chart oF Accounts which will tell the Accounting frameowrk based on which the Chart Of Accounts has been created
    @objects: setting the default Model Manager to the BankAccountModelManager

    
    Some Meta Information: (Additional data points regarding this model that may alter its behavior)

    @abstract: This is a abstract class and will be used through inheritance. Separate implementation can be done for this abstract class.
    [It may also be noted that models are not created for the abstract models, but only for the models which implements the abstract model class]
    @ordering: The default ordering of the table will be based on creation date
    @verbose_name: A human readable name for this Model (Also translatable to other languages with django translation> gettext_lazy)
    @unique_together: the concantanation of coa & account code would remain unique throughout the model i.e database
    @indexes : Index created on different attributes for better db & search queries


    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.OneToOneField('django_ledger.EntityModel',
                                  editable=False,
                                  verbose_name=_('Entity'),
                                  on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    description = models.TextField(verbose_name=_('CoA Description'), null=True, blank=True)
    objects = ChartOfAccountModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Chart of Account')
        verbose_name_plural = _('Chart of Accounts')
        indexes = [
            models.Index(fields=['entity'])
        ]

    def __str__(self):
        return f'{self.slug}: {self.name}'


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Base ChartOfAccounts Model
    """
