from random import choice, randint
from urllib.parse import urlparse
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse

from django_ledger.models import EntityModel, PurchaseOrderModel
from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL
from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.urls.purchase_order import urlpatterns as po_urls

UserModel = get_user_model()


class PurchaseOrderModelTests(DjangoLedgerBaseTest):

    def setUp(self) -> None:
        self.URL_PATTERNS = {
            p.name: set(p.pattern.converters.keys()) for p in po_urls
        }

    def create_purchase_order(self, entity_model: EntityModel) -> PurchaseOrderModel:
        po_title = f'Purchase Order General-{randint(1000, 9999)}'

        po_model = PurchaseOrderModel(po_title=po_title)
        po_model = po_model.configure(entity_slug=entity_model,
                                      user_model=self.user_model,
                                      commit=True)
        return po_model

    def get_purchase_orders(self, entity_model: EntityModel) -> list[PurchaseOrderModel]:
        return PurchaseOrderModel.objects.for_entity(entity_model, self.user_model)

    def test_protected_views(self):
        """
        All Purchase Model Views must have user authenticated.
        If not, user must be redirected to login page.
        """
        self.logout_client()

        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        po_model = self.create_purchase_order(entity_model)

        self.assertEqual(len(self.URL_PATTERNS), 15)
        for path, kwargs in self.URL_PATTERNS.items():
            url_kwargs = dict()
            url_kwargs['entity_slug'] = entity_model.slug
            if 'po_pk' in kwargs:
                url_kwargs['po_pk'] = po_model.uuid
            if 'year' in kwargs:
                url_kwargs['year'] = po_model.date_draft.year
            if 'month' in kwargs:
                url_kwargs['month'] = po_model.date_draft.month 
            if 'ce_pk' in kwargs:
                url_kwargs['ce_pk'] = uuid4()
            if 'po_pk' in kwargs:
                url_kwargs['po_pk'] = uuid4()

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            redirect_response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(redirect_response.url)
            redirect_path = redirect_url.path
            login_path = DJANGO_LEDGER_LOGIN_URL

            self.assertEqual(redirect_response.status_code, 302, msg=f'{path} view is not protected.')
            self.assertEqual(redirect_path, login_path, msg=f'{path} view is not redirecting to correct auth URL')


    def test_purchase_order_list(self):
        """
        Check links and data shown on Purchase Order List page are as supposed to be.
        """
        self.login_client()
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        po_list_url = reverse('django_ledger:po-list', kwargs={'entity_slug': entity_model.slug})

        with self.assertNumQueries(5):
            response = self.CLIENT.get(po_list_url)
        self.assertEqual(response.status_code, 200, msg="Fail to GET Purchase Order list page")

        po_model_qs = response.context['po_list']

        for po_model in po_model_qs:
            po_detail_url = reverse('django_ledger:po-detail', 
                                    kwargs={
                                        'entity_slug': entity_model.slug,
                                        'po_pk': po_model.uuid
                                    })

            po_delete_url = reverse('django_ledger:po-delete',
                                    kwargs={
                                        'entity_slug': entity_model.slug,
                                        'po_pk': po_model.uuid
                                    })
            # contains po-detail and po-delete urls
            self.assertContains(response, po_detail_url)
            self.assertContains(response, po_delete_url)
    

    def test_purchase_order_create(self):
        """
        Check Purchase Order create-page.
        """
        self.login_client()
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)

        po_create_url = reverse('django_ledger:po-create', kwargs={'entity_slug': entity_model.slug})
        response = self.CLIENT.get(po_create_url)

        # purchase order create page is rendered
        self.assertEqual(response.status_code, 200, msg="Fail to GET PO create page")

        # after successfully create a PO, redirect to list
        po_title = f'PO-Create-{randint(1000, 9999)}'
        redirect_response = self.CLIENT.post(po_create_url, data={'po_title': po_title}, follow=False)
        self.assertEqual(redirect_response.status_code, 302, msg="Create PO failed.")

        # check the redirect URL is correct
        redirect_url = urlparse(redirect_response.url)
        redirect_path = redirect_url.path
        list_path = reverse('django_ledger:po-list', kwargs={'entity_slug': entity_model.slug})
        self.assertEqual(redirect_path, list_path, msg="Fail to redirect properly after create a PO")

        # check the created PO is in the list
        response = self.CLIENT.get(redirect_response.url)
        self.assertContains(response, po_title)


    def test_purchase_order_detail(self):
        """
        Check elements on PO detail page.
        """
        self.login_client()
        entity_model: EntityModel = choice(self.ENTITY_MODEL_QUERYSET)
        po_status_dict = dict(PurchaseOrderModel.PO_STATUS)

        po_model_qs = self.get_purchase_orders(entity_model)
        for po_model in po_model_qs:
            po_detail_url = reverse('django_ledger:po-detail',
                                    kwargs={
                                        'entity_slug': entity_model.slug,
                                        'po_pk': po_model.uuid
                                    })
            with self.assertNumQueries(6):
                response = self.CLIENT.get(po_detail_url)
            self.assertEqual(response.status_code, 200, msg=f"Error fetching PO {po_model.uuid} detail.")

            # the correct status is displayed
            self.assertContains(response, po_status_dict[po_model.po_status])

            #TODO
            # assert po-items, assert status changes