from django.contrib.auth import get_user_model
from django.urls import reverse

from django_ledger.models import EntityManagementModel
from django_ledger.tests.base import DjangoLedgerBaseTest

UserModel = get_user_model()


class EntityPermissionTests(DjangoLedgerBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.entity_model = cls.ENTITY_MODEL_QUERYSET.first()

        cls.read_user = UserModel.objects.create_user(
            username='read-manager',
            password='NeverUseThisPassword12345',
            email='read-manager@djangoledger.com',
        )
        cls.write_user = UserModel.objects.create_user(
            username='write-manager',
            password='NeverUseThisPassword12345',
            email='write-manager@djangoledger.com',
        )
        cls.suspended_user = UserModel.objects.create_user(
            username='suspended-manager',
            password='NeverUseThisPassword12345',
            email='suspended-manager@djangoledger.com',
        )

        EntityManagementModel.objects.create(
            entity=cls.entity_model,
            user=cls.read_user,
            permission_level='read',
        )
        EntityManagementModel.objects.create(
            entity=cls.entity_model,
            user=cls.write_user,
            permission_level='write',
        )
        EntityManagementModel.objects.create(
            entity=cls.entity_model,
            user=cls.suspended_user,
            permission_level='suspended',
        )

    def test_read_manager_can_access_read_view(self):
        self.client.force_login(self.read_user)
        response = self.client.get(
            reverse(
                'django_ledger:entity-dashboard',
                kwargs={'entity_slug': self.entity_model.slug},
            ),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_read_manager_cannot_access_write_view(self):
        self.client.force_login(self.read_user)
        response = self.client.get(
            reverse(
                'django_ledger:entity-update',
                kwargs={'entity_slug': self.entity_model.slug},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_write_manager_can_access_write_view(self):
        self.client.force_login(self.write_user)
        response = self.client.get(
            reverse(
                'django_ledger:entity-update',
                kwargs={'entity_slug': self.entity_model.slug},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_suspended_manager_cannot_access_read_view(self):
        self.client.force_login(self.suspended_user)
        response = self.client.get(
            reverse(
                'django_ledger:entity-dashboard',
                kwargs={'entity_slug': self.entity_model.slug},
            )
        )
        self.assertEqual(response.status_code, 403)