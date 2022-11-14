from datetime import date
from decimal import Decimal
from random import choice
from urllib.parse import urlparse
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
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

    def create_bill(self, amount: Decimal, draft_date: date = None, is_accrued: bool = False) -> tuple[
        EntityModel, BillModel]:
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        vendor_model: VendorModel = entity_model.vendors.first()
        account_qs = entity_model.get_accounts(
            user_model=self.user_model
        )

        len(account_qs)  # force evaluation

        cash_account = account_qs.filter(role__in=[ASSET_CA_CASH]).first()
        prepaid_account = account_qs.filter(role__in=[ASSET_CA_PREPAID]).first()
        unearned_account = account_qs.filter(role__in=[LIABILITY_CL_DEFERRED_REVENUE]).first()
        dt = self.get_random_date() if not draft_date else draft_date

        bill_model = BillModel()
        ledger_model, bill_model = bill_model.configure(
            entity_slug=entity_model,
            user_model=self.user_model
        )

        bill_model.amount_due = amount
        bill_model.date_draft = dt
        bill_model.vendor = vendor_model
        bill_model.accrue = is_accrued
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
                url_kwargs['year'] = bill_model.date_draft.year
            if 'month' in kwargs:
                url_kwargs['month'] = bill_model.date_draft.month
            if 'po_pk' in kwargs:
                url_kwargs['po_pk'] = uuid4()
            if 'ce_pk' in kwargs:
                url_kwargs['ce_pk'] = uuid4()

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(response.url)
            redirect_path = redirect_url.path
            login_path = DJANGO_LEDGER_LOGIN_URL

            self.assertEqual(response.status_code, 302, msg=f'{path} view is not protected.')
            self.assertEqual(redirect_path, login_path, msg=f'{path} view not redirecting to correct auth URL.')

    def test_bill_list(self):

        self.login_client()
        entity_model = choice(self.ENTITY_MODEL_QUERYSET)
        bill_list_url = reverse('django_ledger:bill-list',
                                kwargs={
                                    'entity_slug': entity_model.slug
                                })

        with self.assertNumQueries(5):
            response = self.CLIENT.get(bill_list_url)

            # bill-list view is rendered...
            self.assertEqual(response.status_code, 200)

        bill_model_qs = response.context['bills']

        for bill_model in bill_model_qs:

            bill_detail_url = reverse('django_ledger:bill-detail',
                                      kwargs={
                                          'entity_slug': entity_model.slug,
                                          'bill_pk': bill_model.uuid
                                      })
            bill_update_url = reverse('django_ledger:bill-update',
                                      kwargs={
                                          'entity_slug': entity_model.slug,
                                          'bill_pk': bill_model.uuid
                                      })
            # bill_delete_url = reverse('django_ledger:bill-delete',
            #                           kwargs={
            #                               'entity_slug': entity_model.slug,
            #                               'bill_pk': bill_model.uuid
            #                           })
            # mark_as_paid_url = reverse('django_ledger:bill-mark-paid',
            #                            kwargs={
            #                                'entity_slug': entity_model.slug,
            #                                'bill_pk': bill_model.uuid
            #                            })

            # bill shows in list...
            self.assertContains(response, bill_model.get_html_id(), status_code=200)

            # amount due shows in list...
            # amt_due_fmt = number_format(bill_model.amount_due, decimal_pos=2, use_l10n=True, force_grouping=True)
            needle = f'id="{bill_model.get_html_amount_due_id()}"'
            self.assertContains(response, needle)

            # amount paid shows in list...
            needle = f'id="{bill_model.get_html_amount_paid_id()}"'
            self.assertContains(response, needle)

            # contains bill-detail url
            self.assertContains(response, bill_detail_url)
            # contains bill-update url
            self.assertContains(response, bill_update_url)
            # contains bill-delete url
            # self.assertContains(response, bill_delete_url)

            # if bill_model.is_approved() and not bill_model.is_paid():
            #     # shows link to mark as paid...
            #     self.assertContains(response, mark_as_paid_url)
            #     with self.assertNumQueries(11):
            #         paid_response = self.CLIENT.get(mark_as_paid_url, follow=False)
            #     self.assertRedirects(paid_response, expected_url=bill_update_url)

            # elif bill_model.is_approved() and bill_model.is_paid():
            #     # if paid, it cannot be paid
            #     self.assertNotContains(response, mark_as_paid_url)

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

    def test_bill_create(self):

        self.login_client()
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)

        bill_create_url = reverse('django_ledger:bill-create',
                                  kwargs={
                                      'entity_slug': entity_model.slug
                                  })

        response = self.CLIENT.get(bill_create_url)

        # bill create form is rendered
        self.assertContains(response,
                            f'id="djl-bill-model-create-form-id"',
                            msg_prefix='Bill create form is not rendered.')

        # user can select a vendor
        self.assertContains(response,
                            'id="djl-bill-create-vendor-select-input"',
                            msg_prefix='Vendor Select input not rendered.')

        # user can select bill terms...
        self.assertContains(response,
                            'id="djl-bill-create-terms-select-input"',
                            msg_prefix='Bill terms input not rendered.')

        # user can select bill terms...
        self.assertContains(response,
                            'id="djl-bill-xref-input"',
                            msg_prefix='Bill XREF input not rendered.')

        # user can select date...
        self.assertContains(response,
                            'id="djl-bill-draft-date-input"',
                            msg_prefix='Bill draft date input not rendered.')

        # user can select cash account...
        self.assertContains(response,
                            'id="djl-bill-cash-account-input"',
                            msg_prefix='Bill cash account input not rendered.')

        # user can select prepaid account...
        self.assertContains(response,
                            'id="djl-bill-prepaid-account-input"',
                            msg_prefix='Bill prepaid account input not rendered.')

        # user can select unearned account...
        self.assertContains(response,
                            'id="djl-bill-unearned-account-input"',
                            msg_prefix='Bill unearned account input not rendered.')

        # user can select unearned account...
        self.assertContains(response,
                            'id="djl-bill-create-button"',
                            msg_prefix='Bill create button not rendered.')

        # user cannot input amount due...
        self.assertNotContains(response,
                               'id="djl-bill-amount-due-input"',
                               msg_prefix='Bill amount due input not rendered.')

        # user can navigate to bill list
        bill_list_url = reverse('django_ledger:bill-list',
                                kwargs={
                                    'entity_slug': entity_model.slug
                                })
        self.assertContains(response, bill_list_url)

        account_qs = entity_model.get_accounts(
            user_model=self.user_model
        )

        # account_queryset = entity_model.
        a_vendor_model = VendorModel.objects.for_entity(
            entity_slug=entity_model.slug,
            user_model=self.user_model
        ).first()

        bill_data = {
            'vendor': a_vendor_model.uuid,
            'date_draft': localdate(),
            'terms': BillModel.TERMS_NET_30
        }

        create_response = self.CLIENT.post(bill_create_url, data=bill_data, follow=True)
        # self.assert
        # self.assertFormError(create_response, form='form', field=None,
        #                      errors=['Must provide a cash account.'])
        #
        # bill_data['cash_account'] = account_qs.with_roles(roles=ASSET_CA_CASH).first().uuid
        # create_response = self.CLIENT.post(bill_create_url, data=bill_data, follow=True)
        # self.assertFormError(create_response, form='form', field=None,
        #                      errors=['Must provide all accounts Cash, Prepaid, UnEarned.'])
        #
        # cash_account = account_qs.with_roles(roles=ASSET_CA_PREPAID).first()
        # bill_data['prepaid_account'] = cash_account.uuid
        # create_response = self.CLIENT.post(bill_create_url, data=bill_data, follow=True)
        # self.assertFormError(create_response, form='form', field=None,
        #                      errors=['Must provide all accounts Cash, Prepaid, UnEarned.'])
        #
        # del bill_data['prepaid_account']
        # unearned_account = account_qs.with_roles(roles=LIABILITY_CL_DEFERRED_REVENUE).first()
        # bill_data['unearned_account'] = unearned_account.uuid
        # create_response = self.CLIENT.post(bill_create_url, data=bill_data, follow=True)
        # self.assertFormError(create_response, form='form', field=None,
        #                      errors=['Must provide all accounts Cash, Prepaid, UnEarned.'])
        #
        # bill_data['prepaid_account'] = cash_account.uuid
        # create_response = self.CLIENT.post(bill_create_url, data=bill_data, follow=True)
        # self.assertTrue(create_response.resolver_match.view_name, 'django_ledger:bill-detail')

    def test_bill_detail(self):
        self.login_client()
        today = localdate()

        for i in range(5):
            entity_model, bill_model = self.create_bill(amount=Decimal('0.00'), draft_date=today)
            vendor_model: VendorModel = bill_model.vendor
            bill_detail_url = reverse('django_ledger:bill-detail',
                                      kwargs={
                                          'entity_slug': entity_model.slug,
                                          'bill_pk': bill_model.uuid
                                      })

            with self.assertNumQueries(8):
                bill_detail_response = self.CLIENT.get(bill_detail_url)
            self.assertTrue(bill_detail_response.status_code, 200)

            self.assertTrue(bill_model.is_draft())
            # 'Not Approved' is displayed to the user...
            self.assertFalse(bill_model.is_approved())

            # bill card is displayed to the user...
            self.assertContains(bill_detail_response, 'id="djl-bill-card-widget"')

            # vendor card is displayed to the user...
            self.assertContains(bill_detail_response, 'id="djl-vendor-card-widget"')

            # if bill is not approved or draft...
            # user can update bill
            # self.assertContains(bill_detail_response, 'id="djl-bill-detail-update-button"')
            # user cannot mark as paid
            # self.assertNotContains(bill_detail_response, 'id="djl-bill-detail-mark-paid-button"')
            # user can delete..
            # self.assertContains(bill_detail_response, 'id="djl-bill-detail-delete-button"')
            # user cannot void...
            # self.assertNotContains(bill_detail_response, 'id="djl-bill-detail-void-button"')

            # user can navigate to bill-list...
            self.assertContains(bill_detail_response,
                                reverse('django_ledger:bill-list',
                                        kwargs={
                                            'entity_slug': entity_model.slug
                                        }))

            # vendor name is shown
            self.assertContains(bill_detail_response, vendor_model.vendor_name)

            # can edit vendor link
            self.assertContains(bill_detail_response,
                                reverse('django_ledger:vendor-update',
                                        kwargs={
                                            'entity_slug': entity_model.slug,
                                            'vendor_pk': vendor_model.uuid
                                        }))

            # link to cash account detail
            self.assertContains(bill_detail_response,
                                reverse('django_ledger:account-detail',
                                        kwargs={
                                            'entity_slug': entity_model.slug,
                                            'account_pk': bill_model.cash_account.uuid
                                        }))

            # amount paid is shown
            self.assertContains(bill_detail_response, 'id="djl-bill-detail-amount-paid"')

            # amount owed is shown
            self.assertContains(bill_detail_response, 'id="djl-bill-detail-amount-owed"')

            if not bill_model.accrue:
                # amount prepaid is not shown
                self.assertNotContains(bill_detail_response, ' id="djl-bill-detail-amount-prepaid"')
                # amount unearned is not shown
                self.assertNotContains(bill_detail_response, ' id="djl-bill-detail-amount-unearned"')

            else:
                # amount prepaid is shown
                self.assertContains(bill_detail_response, ' id="djl-bill-detail-amount-prepaid"')
                # amount unearned is shown
                self.assertContains(bill_detail_response, ' id="djl-bill-detail-amount-unearned"')

            # amounts are zero...
            self.assertEqual(bill_model.get_amount_cash(), Decimal('0.00'))
            self.assertEqual(bill_model.get_amount_earned(), Decimal('0.00'))
            self.assertEqual(bill_model.get_amount_open(), Decimal('0.00'))
            self.assertEqual(bill_model.get_amount_prepaid(), Decimal('0.00'))
            self.assertEqual(bill_model.get_amount_unearned(), Decimal('0.00'))
