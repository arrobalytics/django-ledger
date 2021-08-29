from django.urls import reverse

from tests.base import DjangoLedgerBaseTest
from tests.settings import LOGIN_URL


class AuthTest(DjangoLedgerBaseTest):
    TEST_URLS = [
        reverse('django_ledger:home'),
        reverse('django_ledger:entity-dashboard',
                kwargs={
                    'entity_slug': 'fake-123'
                })
    ]

    def test_user_is_redirected(self):
        for test_url in self.TEST_URLS:
            response = self.client.get(test_url, follow=False)
            login_url = LOGIN_URL + f'?next={test_url}'
            self.assertRedirects(response, expected_url=login_url)

    def test_login_form(self):
        response = self.client.get(LOGIN_URL)
        self.assertContains(response, text='id="djl-el-login-form"', status_code=200, count=1)
        self.assertContains(response, text='id="djl-el-login-form-username-field"', status_code=200, count=1)
        self.assertContains(response, text='id="djl-el-login-form-password-field"', status_code=200, count=1)

    def test_user_with_wrong_credentials(self):
        response = self.client.post(LOGIN_URL, data={
            'username': self.USERNAME,
            'password': self.PASSWORD + '1',
        }, follow=False)
        self.assertContains(response, text='Login', status_code=200)
        self.assertFormError(response,
                             field=None,
                             form='form',
                             errors=[
                                 'Please enter a correct username and password. Note that both fields may be case-sensitive.'
                             ])

        response = self.client.post(LOGIN_URL, data={
            'username': self.USERNAME + 'abc',
            'password': self.PASSWORD,
        }, follow=False)
        self.assertContains(response, text='Login', status_code=200)
        self.assertFormError(response,
                             field=None,
                             form='form',
                             errors=[
                                 'Please enter a correct username and password. Note that both fields may be case-sensitive.'
                             ])

    def test_user_login(self):
        response = self.client.post(LOGIN_URL, data={
            'username': self.USERNAME,
            'password': self.PASSWORD,
        }, follow=False)
        expeced_url = reverse('django_ledger:home')
        self.assertRedirects(response, expected_url=expeced_url)

    def test_user_can_logout(self):
        home_url = reverse('django_ledger:home')
        login_url = reverse('django_ledger:login')
        logout_url = reverse('django_ledger:logout')
        self.client.login(
            username=self.USERNAME,
            password=self.PASSWORD
        )
        response = self.client.get(home_url)

        # logout button is present...
        self.assertContains(response, text='id="djl-el=logout-button-nav"')

        response = self.client.get(logout_url)
        self.assertRedirects(response, expected_url=login_url)

