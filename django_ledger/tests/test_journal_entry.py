from django_ledger.models import EntityModel, JournalEntryModel, TransactionModel, AccountModel
from django_ledger.tests.base import DjangoLedgerBaseTest
from random import choice
from django_ledger.urls.journal_entry import urlpatterns as journal_entry_urls
from django.urls import reverse

class JournalEntryModelTest(DjangoLedgerBaseTest):

    def setUp(self) -> None:
        self.URL_PATTERNS= {
            p.name: set(p.pattern.converters.keys()) for p in journal_entry_urls
        }

    def get_absolute_url(self, path):
        """
        Generates a specified Journal Entry View URL path.
        with randomly populated entity, ledger, journal entry & transactions.
        """
        
        self.assertTrue(self.URL_PATTERNS.get(path))

        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        ledger_model = self.get_random_ledger(entity_model=entity_model)
        je_model = self.get_random_je(entity_model=entity_model, ledger_model=ledger_model)
        self.get_random_transactions(entity_model=entity_model, je_model=je_model)
        
        url_kwargs = dict()
        kwargs = self.URL_PATTERNS.get(path)
        url_kwargs['entity_slug'] = entity_model.slug
        if 'ledger_pk' in kwargs:
            url_kwargs['ledger_pk'] = ledger_model.uuid
        if 'je_pk' in kwargs:
            url_kwargs['je_pk'] = je_model.uuid
        if 'year' in kwargs:
            url_kwargs['year'] = je_model.timestamp.year
        if 'month' in kwargs:
            url_kwargs['month'] = je_model.timestamp.month
        
        return {
            'url':reverse(f'django_ledger:{path}', kwargs=url_kwargs),
            'entity_model':entity_model,
            'ledger_model':ledger_model,
            'je_model':je_model,
        }
    
    def test_protected_views(self):
        """
        All Journal Entry Views must have user authenticated.
        If not, user must be redirected to login page.
        """
        self.logout_client()

        for path in self.URL_PATTERNS.keys():
            url_info = self.get_absolute_url(path=path)
            redirect_response = self.CLIENT.get(url_info["url"], follow=False)
            self.assertEqual(redirect_response.status_code, 302, 
                             msg=f'{path} view is not protected.')

    def test_journal_entry_detail_view(self):
        """
        Check datas shown on Journal Entry Detail view are as supposed to be.
        """
        self.login_client()

        url_info = self.get_absolute_url(path='je-detail')
        url = url_info['url']
        response = self.CLIENT.get(url)
        self.assertEqual(response.status_code, 200, 
                         msg="Fail to GET Purchase Order list page")
        
        je_model = url_info['je_model']
        
        transactions_qs = je_model.get_transaction_queryset()
        
        for transaction in transactions_qs:
            self.assertContains(response, transaction.account.code)
            self.assertContains(response, transaction.account.name)
            self.assertContains(response, transaction.description)
        
        url_kwargs = {
                        'entity_slug': url_info['entity_model'].slug,
                        'ledger_pk': url_info['ledger_model'].uuid,
                        'je_pk': url_info['je_model'].uuid
                    }
        je_detail_txs_url = reverse('django_ledger:je-detail-txs', kwargs=url_kwargs)
        je_update_url = reverse('django_ledger:je-update', kwargs=url_kwargs)
        
        self.assertContains(response, je_detail_txs_url, 
                            msg_prefix="Link to Journal Entry Transaction Detail is not displayed")
        self.assertContains(response, je_update_url, 
                            msg_prefix="Link to go back to Journal Entry Edit view is not displayed")
         