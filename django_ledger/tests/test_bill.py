from datetime import date
from decimal import Decimal
from random import choice
from urllib.parse import urlparse
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.timezone import localdate

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import EntityModel, BillModel, VendorModel
from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL
from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.urls.bill import urlpatterns as bill_urls

UserModel = get_user_model()


class BillModelTests(DjangoLedgerBaseTest):

    def setUp(self) -> None:
        self.URL_PATTERNS = {
            p.name: set(p.pattern.converters.keys()) for p in bill_urls
        }

    def create_bill(self, amount: Decimal, date: date = None) -> tuple[EntityModel, BillModel]:
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        vendor_model: VendorModel = entity_model.vendors.first()
        account_qs = entity_model.coa.accounts.all()
        len(account_qs)  # force evaluation

        cash_account = account_qs.filter(role__in=[ASSET_CA_CASH]).first()
        prepaid_account = account_qs.filter(role__in=[ASSET_CA_PREPAID]).first()
        unearned_account = account_qs.filter(role__in=[LIABILITY_CL_DEFERRED_REVENUE]).first()
        dt = self.get_random_date() if not date else date

        bill_model = BillModel()
        ledger_model, bill_model = bill_model.configure(
            entity_slug=entity_model,
            user_model=self.user_model
        )

        bill_model.amount_due = amount
        bill_model.date = dt
        bill_model.vendor = vendor_model
        bill_model.xref = 'ABC123xref'
        bill_model.cash_account = cash_account
        bill_model.prepaid_account = prepaid_account
        bill_model.unearned_account = unearned_account
        bill_model.clean()
        bill_model.save()

        return entity_model, bill_model

    def test_protected_views(self):
        """
        All Bill Model views must have user authenticated.
        If not, user must be redirected to login page.
        """

        self.logout_client()

        entity_model, bill_model = self.create_bill(amount=Decimal('500.00'))

        for path, kwargs in self.URL_PATTERNS.items():
            url_kwargs = dict()
            url_kwargs['entity_slug'] = entity_model.slug
            if 'bill_pk' in kwargs:
                url_kwargs['bill_pk'] = bill_model.uuid
            if 'year' in kwargs:
                url_kwargs['year'] = bill_model.date.year
            if 'month' in kwargs:
                url_kwargs['month'] = bill_model.date.month
            if 'po_pk' in kwargs:
                url_kwargs['po_pk'] = uuid4()

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(response.url)
            redirect_path = redirect_url.path
            login_path = DJANGO_LEDGER_LOGIN_URL

            self.assertEqual(response.status_code, 302, msg=f'{path} view is not protected.')
            self.assertEqual(redirect_path, login_path, msg=f'{path} view not redirecting to correct auth URL.')

    def test_bill_list(self):

        self.login_client()

        entity_model, bill_model = self.create_bill(
            amount=Decimal('1000.00'),
            date=localdate())
        bill_list_url = reverse('django_ledger:bill-list',
                                kwargs={
                                    'entity_slug': entity_model.slug
                                })

        response = self.CLIENT.get(bill_list_url)

        # bill-list view is rendered...
        self.assertEqual(response.status_code, 200)

        # bill shows in list...
        self.assertContains(response, bill_model.get_html_id(), status_code=200)

        # amount due shows in list...
        amt_due_fmt = number_format(bill_model.amount_due, decimal_pos=2, use_l10n=True, force_grouping=True)
        needle = f'<td id="{bill_model.get_html_amount_due_id()}">${amt_due_fmt}</td>'
        self.assertContains(response, needle)

        # amount paid shows in list...
        needle = f'<td id="{bill_model.get_html_amount_paid_id()}">$0</td>'
        self.assertContains(response, needle)

        # # making one payment...
        # bill_model.make_payment(amt=Decimal('250.50'),
        #                         entity_slug=entity_model.slug,
        #                         user_model=self.user_model,
        #                         commit=True)
        #
        # response = self.CLIENT.get(bill_list_url)
        # amt_paid = number_format(bill_model.amount_paid, decimal_pos=2, use_l10n=True, force_grouping=True)
        # needle = f'<td id="{bill_model.get_html_amount_paid_id()}">${amt_paid}</td>'
        # self.assertEqual(bill_model.amount_paid, Decimal('250.50'))
        # self.assertContains(response, needle)
        #
        # # making additional payment...
        # bill_model.make_payment(amt=Decimal('125.60'),
        #                         entity_slug=entity_model.slug,
        #                         user_model=self.user_model,
        #                         commit=True)
        # response = self.CLIENT.get(bill_list_url)
        # amt_paid = number_format(bill_model.amount_paid, decimal_pos=2, use_l10n=True, force_grouping=True)
        # needle = f'<td id="{bill_model.get_html_amount_paid_id()}">${amt_paid}</td>'
        # self.assertEqual(bill_model.amount_paid, Decimal('376.10'))
        # self.assertContains(response, needle)
        #
        # # mark as paid...
        # bill_model.mark_as_paid(entity_slug=entity_model.slug,
        #                         user_model=self.user_model,
        #                         commit=True)
        # response = self.CLIENT.get(bill_list_url)
        # amt_paid = number_format(bill_model.amount_paid, decimal_pos=2, use_l10n=True, force_grouping=True)
        # needle = f'<td id="{bill_model.get_html_amount_paid_id()}">${amt_paid}</td>'
        # self.assertEqual(bill_model.amount_paid, bill_model.amount_due)
        # self.assertContains(response, needle)
