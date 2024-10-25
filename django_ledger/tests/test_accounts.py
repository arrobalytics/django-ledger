from random import choice
from urllib.parse import urlparse

from django.urls import reverse

from django_ledger.forms.account import AccountModelCreateForm
from django_ledger.io import roles, CREDIT
from django_ledger.models import EntityModel
from django_ledger.models.accounts import AccountModel
from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.urls.account import urlpatterns as account_urls


class AccountModelTests(DjangoLedgerBaseTest):
    N = 2

    def setUp(self):
        self.resolve_url_patterns(
            url_patterns=account_urls
        )

    def test_protected_views(self):

        self.logout_client()
        entity_model = self.get_random_entity_model()
        account_model: AccountModel = self.get_random_account(entity_model=entity_model)

        for path, kwargs in self.URL_PATTERNS.items():
            url_kwargs = dict()
            url_kwargs['entity_slug'] = entity_model.slug

            if 'coa_slug' in kwargs:
                url_kwargs['coa_slug'] = account_model.coa_slug
            if 'account_pk' in kwargs:
                url_kwargs['account_pk'] = account_model.uuid
            if 'year' in kwargs:
                url_kwargs['year'] = self.get_random_date().year
            if 'quarter' in kwargs:
                url_kwargs['quarter'] = choice(range(1, 5))
            if 'month' in kwargs:
                url_kwargs['month'] = self.get_random_date().month
            if 'day' in kwargs:
                url_kwargs['day'] = choice(range(1, 29))

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(response.url)
            redirect_path = redirect_url.path
            login_path = reverse(viewname='django_ledger:login')

            self.assertEqual(response.status_code, 302, msg=f'{path} view is not protected.')
            self.assertEqual(redirect_path, login_path, msg=f'{path} view not redirecting to correct auth URL.')

    def test_account_create(self):

        entity_model = self.get_random_entity_model()
        account_create_url = reverse(
            viewname='django_ledger:account-create',
            kwargs={
                'entity_slug': entity_model.slug,
                'coa_slug': entity_model.default_coa_slug
            }
        )

        self.login_client()
        response = self.CLIENT.get(account_create_url)

        # check if user can access page...
        self.assertEqual(response.status_code, 200, msg="Fail to GET Account Create page.")

        # check if account create form is rendered...
        account_create_form: AccountModelCreateForm = response.context['form']
        self.assertContains(response, account_create_form.form_id, count=1)

        # check if all fields are rendered...
        self.assertContains(response, 'name="code"')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="role"')
        self.assertContains(response, 'name="role_default"')
        self.assertContains(response, 'name="balance_type"')
        self.assertContains(response, 'name="active"')
        self.assertContains(response, 'name="coa_model"')

        # creates new account...
        NEW_ACCOUNT_CODE = '404000'
        form_data = {
            'code': NEW_ACCOUNT_CODE,
            'name': 'Test Income Account',
            'role': roles.INCOME_OPERATIONAL,
            'role_default': False,
            'balance_type': CREDIT,
            'active': True
        }
        response_create = self.CLIENT.post(account_create_url, data=form_data)
        self.assertEqual(response_create.status_code, 302)
        self.assertTrue(AccountModel.objects.for_entity(
            entity_model=entity_model,
            user_model=self.user_model,
            coa_slug=entity_model.default_coa_slug,
        ).with_codes(codes=NEW_ACCOUNT_CODE).exists())

        # cannot create an account with same code again...
        response_create = self.CLIENT.post(account_create_url, data=form_data)
        self.assertEqual(response_create.status_code, 200)
        self.assertContains(response_create, 'Account with this Chart of Accounts and Account Code already exists')

    def test_account_activation(self):

        entity_model: EntityModel = self.get_random_entity_model()
        account_model: AccountModel = self.get_random_account(entity_model=entity_model, active=True)

        self.assertTrue(account_model.can_deactivate())
        self.assertTrue(account_model.active)

        account_model.deactivate(commit=True)
        self.assertFalse(account_model.can_deactivate())
        self.assertFalse(account_model.active)

        account_model.activate(commit=True)
        self.assertTrue(account_model.can_deactivate())
        self.assertTrue(account_model.active)

    def test_account_lock(self):
        entity_model: EntityModel = self.get_random_entity_model()
        account_model: AccountModel = self.get_random_account(entity_model=entity_model, active=True, locked=False)

        self.assertTrue(account_model.can_lock())
        self.assertFalse(account_model.can_unlock())

        account_model.lock(commit=True)
        self.assertFalse(account_model.can_lock())
        self.assertTrue(account_model.can_unlock())

        account_model.unlock(commit=True)
        self.assertTrue(account_model.can_lock())
        self.assertFalse(account_model.can_unlock())

    def test_annotations(self):
        entity_model: EntityModel = self.get_random_entity_model()
        account_model: AccountModel = self.get_random_account(entity_model=entity_model, active=True, locked=False)

        self.assertEqual(account_model.entity_slug, entity_model.slug)
        self.assertEqual(account_model.coa_slug, account_model.coa_model.slug)
        self.assertEqual(account_model.coa_model.active, account_model.is_coa_active())

    def test_can_transact(self):
        entity_model: EntityModel = self.get_random_entity_model()
        account_model: AccountModel = self.get_random_account(entity_model=entity_model, active=True, locked=False)
        self.assertTrue(account_model.can_transact())
        account_model.lock(commit=False)
        self.assertFalse(account_model.can_transact())
        account_model.unlock(commit=False)
