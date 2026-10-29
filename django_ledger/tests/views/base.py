"""
Shared helpers for Django Ledger view security and behavior tests.
"""
from __future__ import annotations

import importlib
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import URLPattern, reverse

from django_ledger.models import EntityModel
from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.views.mixins import DjangoLedgerActionViewMixIn

UserModel = get_user_model()

FOREIGN_ENTITY_SLUG = 'not-authorized-entity-xyz'


class DjangoLedgerViewTestCase(DjangoLedgerBaseTest):
    """
    Base class for per-domain view security tests.

    Subclasses set URL_MODULE to a django_ledger.urls.* module path and inherit
    the standard authentication, authorization, and action-method suites.
    """

    # Keep sample data light so the per-module suites stay practical.
    N = 1
    TX_QUANTITY = 5

    URL_MODULE: Optional[str] = None
    # URL names that are intentionally public or have special auth rules.
    PUBLIC_URL_NAMES: Tuple[str, ...] = ()
    # Skip building/hitting these URL names entirely.
    SKIP_URL_NAMES: Tuple[str, ...] = ()
    # URL names that mutate state and must reject GET with HTTP 405.
    # Detected automatically via DjangoLedgerActionViewMixIn; extend as needed.
    EXTRA_ACTION_URL_NAMES: Tuple[str, ...] = ()
    # URL names expected to allow GET for authenticated users (list/create/detail).
    # If empty, all non-action entity-scoped GET views are checked.
    READ_OK_URL_NAMES: Tuple[str, ...] = ()
    # Names containing these tokens need extra workflow state and are skipped
    # by the authorized GET smoke test.
    SKIP_SAFE_GET_TOKENS: Tuple[str, ...] = (
        'create-po',
        'create-estimate',
        'update-items',
        'force-migrate',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._url_entries = cls._load_url_entries()

    @classmethod
    def _load_url_entries(cls) -> List[Dict[str, Any]]:
        if not cls.URL_MODULE:
            return []
        module = importlib.import_module(cls.URL_MODULE)
        entries: List[Dict[str, Any]] = []
        for pattern in getattr(module, 'urlpatterns', []):
            if not isinstance(pattern, URLPattern) or not pattern.name:
                continue
            view_cls = getattr(pattern.callback, 'view_class', None)
            is_action = bool(
                view_cls and issubclass(view_cls, DjangoLedgerActionViewMixIn)
            )
            if pattern.name in cls.EXTRA_ACTION_URL_NAMES:
                is_action = True
            entries.append(
                {
                    'name': pattern.name,
                    'converters': set(pattern.pattern.converters.keys()),
                    'view_class': view_cls,
                    'is_action': is_action,
                }
            )
        return entries

    def get_url_entries(self) -> List[Dict[str, Any]]:
        return [
            entry
            for entry in self._url_entries
            if entry['name'] not in self.SKIP_URL_NAMES
        ]

    def get_entity_model(self) -> EntityModel:
        return self.get_random_entity_model()

    def _first_or_none(self, qs):
        if qs is None:
            return None
        # Avoid QuerySet.first() after slicing (Django forbids reorder).
        for obj in qs[:1]:
            return obj
        return None

    def build_url_kwargs(
        self,
        converters: Iterable[str],
        entity_model: Optional[EntityModel] = None,
        *,
        foreign_entity: bool = False,
        url_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build reverse() kwargs for a URL pattern.

        Returns None when a required object fixture is unavailable.
        """
        entity_model = entity_model or self.get_entity_model()
        converters = set(converters)
        url_name = url_name or ''
        kwargs: Dict[str, Any] = {}

        if 'entity_slug' in converters:
            kwargs['entity_slug'] = (
                FOREIGN_ENTITY_SLUG if foreign_entity else entity_model.slug
            )

        today = date.today()
        if 'year' in converters:
            kwargs['year'] = today.year
        if 'month' in converters:
            kwargs['month'] = today.month
        if 'day' in converters:
            kwargs['day'] = min(today.day, 28)
        if 'quarter' in converters:
            kwargs['quarter'] = ((today.month - 1) // 3) + 1

        if 'coa_slug' in converters:
            coa = entity_model.get_default_coa()
            if coa is None:
                return None
            kwargs['coa_slug'] = coa.slug

        if 'account_pk' in converters:
            account = self._first_or_none(entity_model.get_coa_accounts(active=False))
            if account is None:
                return None
            kwargs['account_pk'] = account.uuid

        if 'ledger_pk' in converters:
            ledger = self._first_or_none(entity_model.get_ledgers())
            if ledger is None:
                return None
            kwargs['ledger_pk'] = ledger.uuid

        if 'je_pk' in converters:
            ledger_pk = kwargs.get('ledger_pk')
            if ledger_pk is None:
                ledger = self._first_or_none(entity_model.get_ledgers())
                if ledger is None:
                    return None
                kwargs['ledger_pk'] = ledger.uuid
                ledger_pk = ledger.uuid
            from django_ledger.models import JournalEntryModel

            je = self._first_or_none(JournalEntryModel.objects.for_ledger(ledger_pk))
            if je is None:
                return None
            kwargs['je_pk'] = je.uuid

        if 'bill_pk' in converters:
            bill = self._first_or_none(entity_model.get_bills())
            if bill is None:
                return None
            kwargs['bill_pk'] = bill.uuid

        if 'invoice_pk' in converters:
            invoice = self._first_or_none(entity_model.get_invoices())
            if invoice is None:
                return None
            kwargs['invoice_pk'] = invoice.uuid

        if 'po_pk' in converters:
            po = self._first_or_none(entity_model.get_purchase_orders())
            if po is None:
                return None
            kwargs['po_pk'] = po.uuid

        if 'ce_pk' in converters:
            estimate = self._first_or_none(entity_model.get_estimates())
            if estimate is None:
                return None
            kwargs['ce_pk'] = estimate.uuid

        if 'customer_pk' in converters:
            customer = self._first_or_none(entity_model.get_customers())
            if customer is None:
                return None
            kwargs['customer_pk'] = customer.uuid

        if 'vendor_pk' in converters:
            vendor = self._first_or_none(entity_model.get_vendors())
            if vendor is None:
                return None
            kwargs['vendor_pk'] = vendor.uuid

        if 'bank_account_pk' in converters:
            bank_account = self._first_or_none(entity_model.bankaccountmodel_set.all())
            if bank_account is None:
                return None
            kwargs['bank_account_pk'] = bank_account.uuid

        if 'unit_slug' in converters:
            unit = self._first_or_none(entity_model.entityunitmodel_set.all())
            if unit is None:
                return None
            kwargs['unit_slug'] = unit.slug

        if 'uom_pk' in converters:
            uom = self._first_or_none(entity_model.unitofmeasuremodel_set.all())
            if uom is None:
                return None
            kwargs['uom_pk'] = uom.uuid

        if 'item_pk' in converters:
            item_qs = entity_model.itemmodel_set.all()
            if 'product' in url_name:
                item_qs = item_qs.products()
            elif 'service' in url_name:
                item_qs = item_qs.services()
            elif 'expense' in url_name:
                item_qs = item_qs.expenses()
            elif 'inventory-item' in url_name:
                item_qs = item_qs.inventory_wip()
            item = self._first_or_none(item_qs)
            if item is None:
                return None
            kwargs['item_pk'] = item.uuid

        if 'closing_entry_pk' in converters:
            closing_entry = self._first_or_none(entity_model.closingentrymodel_set.all())
            if closing_entry is None:
                return None
            kwargs['closing_entry_pk'] = closing_entry.uuid

        if 'receipt_pk' in converters:
            receipt = self._first_or_none(entity_model.get_receipts())
            if receipt is None:
                return None
            kwargs['receipt_pk'] = receipt.uuid

        if 'receipt_type' in converters:
            kwargs['receipt_type'] = 'sales'

        if 'job_pk' in converters:
            from django_ledger.models import ImportJobModel

            job = self._first_or_none(
                ImportJobModel.objects.for_entity(entity_model=entity_model)
            )
            if job is None:
                return None
            kwargs['job_pk'] = job.uuid

        if 'staged_tx_pk' in converters:
            job_pk = kwargs.get('job_pk')
            if job_pk is None:
                return None
            from django_ledger.models import ImportJobModel

            job = ImportJobModel.objects.filter(uuid=job_pk).first()
            if job is None:
                return None
            staged = self._first_or_none(job.stagedtransactionmodel_set.all())
            if staged is None:
                return None
            kwargs['staged_tx_pk'] = staged.uuid

        # Any leftover unknown converters get a random UUID placeholder.
        for key in converters:
            if key not in kwargs:
                if key.endswith('_pk') or key.endswith('_uuid'):
                    kwargs[key] = uuid4()
                else:
                    kwargs[key] = 'placeholder'

        return kwargs

    def reverse_entry(
        self,
        entry: Dict[str, Any],
        entity_model: Optional[EntityModel] = None,
        *,
        foreign_entity: bool = False,
    ) -> Optional[str]:
        kwargs = self.build_url_kwargs(
            entry['converters'],
            entity_model=entity_model,
            foreign_entity=foreign_entity,
            url_name=entry['name'],
        )
        if kwargs is None:
            return None
        return reverse(f"django_ledger:{entry['name']}", kwargs=kwargs)

    def assert_login_redirect(self, url: str, msg: str = ''):
        response = self.CLIENT.get(url, follow=False)
        self.assertEqual(
            response.status_code,
            302,
            msg=msg or f'Expected login redirect for {url}, got {response.status_code}',
        )
        redirect_path = urlparse(response.url).path
        login_path = reverse('django_ledger:login')
        self.assertEqual(
            redirect_path,
            login_path,
            msg=msg or f'{url} did not redirect to login ({redirect_path})',
        )

    def test_urls_require_authentication(self):
        """
        Anonymous users must be sent to login for every protected URL.
        """
        if not self.URL_MODULE:
            self.skipTest('URL_MODULE not configured')

        self.logout_client()
        entity_model = self.get_entity_model()
        checked = 0

        for entry in self.get_url_entries():
            if entry['name'] in self.PUBLIC_URL_NAMES:
                continue
            url = self.reverse_entry(entry, entity_model=entity_model)
            if url is None:
                continue
            self.assert_login_redirect(
                url,
                msg=f'{entry["name"]} must require authentication',
            )
            checked += 1

        if checked == 0:
            self.skipTest(f'No protected URLs were exercised for {self.URL_MODULE}')

    def test_urls_deny_unauthorized_entity(self):
        """
        Authenticated users must not access another business's entity slug.
        """
        if not self.URL_MODULE:
            self.skipTest('URL_MODULE not configured')

        self.login_client()
        entity_model = self.get_entity_model()
        checked = 0

        for entry in self.get_url_entries():
            if entry['name'] in self.PUBLIC_URL_NAMES:
                continue
            if 'entity_slug' not in entry['converters']:
                continue
            url = self.reverse_entry(
                entry,
                entity_model=entity_model,
                foreign_entity=True,
            )
            if url is None:
                continue
            response = self.CLIENT.get(url, follow=False)
            self.assertIn(
                response.status_code,
                {403, 404, 405},
                msg=(
                    f'{entry["name"]} must deny unauthorized entity access, '
                    f'got {response.status_code}'
                ),
            )
            checked += 1

        if checked == 0:
            self.skipTest('No entity-scoped URLs in this module')

    def test_action_urls_reject_get(self):
        """
        Accounting workflow actions must reject GET with HTTP 405.
        """
        if not self.URL_MODULE:
            self.skipTest('URL_MODULE not configured')

        action_entries = [e for e in self.get_url_entries() if e['is_action']]
        if not action_entries:
            self.skipTest('No action URLs in this module')

        self.login_client()
        entity_model = self.get_entity_model()
        checked = 0

        for entry in action_entries:
            url = self.reverse_entry(entry, entity_model=entity_model)
            if url is None:
                continue
            response = self.CLIENT.get(url, follow=False)
            self.assertEqual(
                response.status_code,
                405,
                msg=f'{entry["name"]} GET must return 405, got {response.status_code}',
            )
            view_cls = entry.get('view_class')
            if view_cls and issubclass(view_cls, DjangoLedgerActionViewMixIn):
                body = response.content.decode(errors='ignore').lower()
                self.assertIn('post', body)
                self.assertIn('get', body)
            checked += 1

        if checked == 0:
            self.skipTest(
                f'No action URLs could be reversed for {self.URL_MODULE}'
            )

    def test_authorized_user_can_get_safe_views(self):
        """
        Logged-in entity managers can open list/create/detail pages with GET.
        """
        if not self.URL_MODULE:
            self.skipTest('URL_MODULE not configured')

        self.login_client()
        entity_model = self.get_entity_model()
        checked = 0

        for entry in self.get_url_entries():
            if entry['is_action']:
                continue
            if entry['name'] in self.PUBLIC_URL_NAMES:
                continue
            if any(token in entry['name'] for token in self.SKIP_SAFE_GET_TOKENS):
                continue
            if self.READ_OK_URL_NAMES and entry['name'] not in self.READ_OK_URL_NAMES:
                continue
            # Prefer list/create/detail-style endpoints for the smoke check.
            if self.READ_OK_URL_NAMES or any(
                token in entry['name']
                for token in ('list', 'create', 'detail', 'update', 'dashboard', 'home')
            ):
                url = self.reverse_entry(entry, entity_model=entity_model)
                if url is None:
                    continue
                response = self.CLIENT.get(
                    url,
                    follow=False,
                    raise_request_exception=False,
                )
                self.assertIn(
                    response.status_code,
                    {200, 302},
                    msg=(
                        f'{entry["name"]} should be reachable for an authorized user, '
                        f'got {response.status_code}'
                    ),
                )
                checked += 1

        if checked == 0:
            self.skipTest('No safe GET views available to exercise')
