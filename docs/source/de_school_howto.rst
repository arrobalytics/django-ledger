German School / Bildungsurlaub How-To
=====================================

This guide is for **German training providers** using django-ledger with the
``de`` country plugin — especially **Bildungsurlaub-accredited courses** (online
and in-person), freelance teachers, venue rental, and a small active account set
on top of the full **DATEV SKR03** chart.

It covers setup, daily bookkeeping, tax regimes, and quarterly reporting. For
architecture and plugin internals, see :doc:`regional`.

**Viewing this guide:** it is part of the Sphinx docs. Build locally with
``cd docs && make html`` and open ``docs/build/html/de_school_howto.html``, or
see the **Documentation** section in the README for full instructions.
Published HTML may also appear on Read the Docs when enabled for your fork.

.. contents:: On this page
   :local:
   :depth: 2

Who this is for
---------------

You run (or are setting up) a small school or training business in Germany and want:

- Double-entry bookkeeping with a **real SKR03 chart** (DATEV-compatible codes)
- A **small journal-entry picker** for day-to-day work (~30 accounts, not 2,700)
- **Pluggable VAT behaviour** for three scenarios without code changes:

  1. **Tax-exempt school/training** (§ 4 UStG) — your preferred long-term outcome
  2. **Kleinunternehmer** (§ 19 UStG) — turnover-based small-business exemption
  3. **Standard VAT** (Regelbesteuerung) — if neither exemption applies

- **Quarterly summaries** for ELSTER planning or Kleinunternehmer turnover checks

What this guide does *not* replace: legal/tax advice, ELSTER submission, or your
Steuerberater's final numbers. Use the reports here as **working figures** from
your ledger.

Prerequisites
-------------

- A working Django project with django-ledger installed (see the main README)
- Migrations applied for ``django_ledger``, ``django_ledger_extensions``, and
  ``django_ledger_countries``
- ``DJANGO_LEDGER_COUNTRY = 'de'`` in settings
- A superuser (or entity admin) to access Django admin and the ledger UI

Initial setup
-------------

Install the regional apps
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       'django_ledger',
       'django_ledger_extensions',   # tax profiles, supporting documents, translations
       'django_ledger_countries',    # DE/US plugins
   ]

Recommended settings for a Bildungsurlaub school
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   DJANGO_LEDGER_COUNTRY = 'de'

   # Full SKR03 from bundled DATEV CSV (Schulen freie Träger)
   DJANGO_LEDGER_DE_DEFAULT_COA = 'skr03'

   # Default tax regime for *new* entities while applications are pending
   DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME = 'exempt'   # or 'small_business' | 'standard'
   DJANGO_LEDGER_DE_DEFAULT_VAT_RATE = '0.19'       # only used when regime is 'standard'

   # Kleinunternehmer turnover limits (§ 19 UStG) for quarterly report warnings
   DJANGO_LEDGER_DE_KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT = 22000
   DJANGO_LEDGER_DE_KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT = 50000

   # Germany default: require a Beleg before posting a journal entry
   # DJANGO_LEDGER_DE_REQUIRE_SUPPORTING_DOCUMENT_ON_POST = True

   # Optional: S3 (or other) storage for receipts
   # DJANGO_LEDGER_SUPPORTING_DOCUMENT_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

Run migrations and create a user:

.. code-block:: shell

   python manage.py migrate
   python manage.py createsuperuser

Create your entity
------------------

1. Log in to the ledger UI (typically ``/ledger/``).
2. Create an **Entity** (your legal business unit — UG, Einzelunternehmen, etc.).
3. On save, the Germany plugin automatically:

   - Creates an **Entity Tax Profile** (regime from ``DEFAULT_TAX_REGIME``)
   - Will populate SKR03 when you run ``sync_skr03`` (or on first CoA population)

Load the SKR03 chart
--------------------

The Germany plugin ships the DATEV export
``2026_Schulen_freie_Träger.csv`` (~2,700 postable accounts). Account codes
keep native DATEV form (e.g. ``1200 00``, ``8100 00``).

.. code-block:: shell

   python manage.py sync_skr03 --entity=your-entity-slug

Options:

.. code-block:: shell

   # Re-import even if accounts already exist
   python manage.py sync_skr03 --entity=your-entity-slug --force

   # Activate every account (not recommended for daily use)
   python manage.py sync_skr03 --entity=your-entity-slug --activate-all

   # Deactivate all non-root accounts
   python manage.py sync_skr03 --entity=your-entity-slug --deactivate-all

After a normal sync, only the **starter account set** matching your entity's tax
regime is ``active=True``. Everything else remains on the chart for reference and
DATEV export but hidden from journal-entry pickers.

Full chart vs starter accounts
------------------------------

+------------------+------------------------+-------------------------------+
|                  | Full SKR03 chart       | Starter (active) accounts     |
+==================+========================+===============================+
| Count            | ~2,700 postable       | ~30 (regime-filtered)         |
+------------------+------------------------+-------------------------------+
| Purpose          | DATEV reference, export| Daily JEs, invoices, bills  |
|                  | future special cases   |                               |
+------------------+------------------------+-------------------------------+
| How to extend    | Chart of accounts UI   | ``DJANGO_LEDGER_DE_          |
|                  | — activate more codes  | SKR03_STARTER_CODES`` or      |
|                  |                        | activate in UI                |
+------------------+------------------------+-------------------------------+

Default starter accounts (Bildungsurlaub school)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These are defined in ``django_ledger_countries/de/coa/starter.py``. Grouped by
purpose:

**Balance sheet / clearing**

.. list-table::
   :header-rows: 1
   :widths: 15 55

   * - Code
     - Typical use
   * - ``0860 00``
     - Opening equity / Gewinnvortrag
   * - ``1200 00``
     - Bank
   * - ``1400 00``
     - Unpaid student invoices (Forderungen)
   * - ``1600 00``
     - Unpaid supplier bills (Verbindlichkeiten)
   * - ``1576 00``
     - Input VAT 19% (**standard regime only**)
   * - ``1776 00``
     - Output VAT 19% (**standard regime only**)

**Course revenue**

.. list-table::
   :header-rows: 1
   :widths: 15 55

   * - Code
     - Typical use
   * - ``8100 00``
     - Tax-exempt revenue (§ 4 UStG) — **exempt regime**
   * - ``8200 00``
     - General revenue — **Kleinunternehmer**
   * - ``8000 00``
     - Sales revenue (freely assignable)
   * - ``8001 10``
     - Enrollment / admission fees
   * - ``8400 00``
     - Taxable revenue 19% — **standard regime**

**People & subcontractors**

.. list-table::
   :header-rows: 1
   :widths: 15 55

   * - Code
     - Typical use
   * - ``3100 11``
     - Freelance teacher honoraria
   * - ``3100 28``
     - Consulting purchased
   * - ``3100 90``
     - Other third-party services

**Premises, equipment, IT**

.. list-table::
   :header-rows: 1
   :widths: 15 55

   * - Code
     - Typical use
   * - ``4210 10``
     - Room rental (in-person courses)
   * - ``4960 00``
     - Equipment / furnishings rental
   * - ``4810 00``
     - Equipment leasing (video gear)
   * - ``0300 10``
     - Capitalized AV / school equipment
   * - ``4805 00``
     - Repairs & maintenance
   * - ``4855 00``
     - Immediate write-off of low-value assets (GWG)
   * - ``4806 00``
     - Hosting / software maintenance
   * - ``4920 00``
     - Telephone / telecom
   * - ``4980 10``
     - IT consumables

**Professional & admin**

.. list-table::
   :header-rows: 1
   :widths: 15 55

   * - Code
     - Typical use
   * - ``4390 10``
     - Accreditation / regulatory fees
   * - ``4950 11``
     - Legal / general consulting
   * - ``4955 00``
     - Steuerberater / bookkeeping
   * - ``4957 00``
     - Year-end closing & audit
   * - ``4360 00``
     - Insurance
   * - ``4600 15``
     - Advertising / course marketing
   * - ``4670 00``
     - Owner travel (site visits, in-person courses)
   * - ``4970 00``
     - Bank / payment fees
   * - ``4997 00``
     - General administration

Override the starter list globally:

.. code-block:: python

   DJANGO_LEDGER_DE_SKR03_STARTER_CODES = [
       '1200 00',
       '8100 00',
       # ...
   ]

Tax regimes (the important part)
--------------------------------

Each entity has one **Entity Tax Profile** (Django admin → *Entity tax profiles*).
The ``tax_regime`` field drives **posting logic**, **active accounts**, and
**quarterly report shape**. You change it when your Finanzamt confirms status —
no code deploy required.

Comparison
~~~~~~~~~~

+------------------+--------------------+--------------------+--------------------+
|                  | ``exempt``         | ``small_business`` | ``standard``       |
+==================+====================+====================+====================+
| Legal basis      | § 4 UStG           | § 19 UStG          | Regelbesteuerung   |
|                  | (school/training)  | (Kleinunternehmer) |                    |
+------------------+--------------------+--------------------+--------------------+
| Charge VAT on    | No                 | No                 | Yes (19% default)  |
| course fees?     |                    |                    |                    |
+------------------+--------------------+--------------------+--------------------+
| USt-Voranmeldung | No (exempt         | No                 | Yes (monthly or    |
| (ELSTER)?        | supplies)          |                    | quarterly)         |
+------------------+--------------------+--------------------+--------------------+
| VAT split on     | No                 | No                 | Yes — net +        |
| invoices/bills?  |                    |                    | Vorsteuer/USt      |
+------------------+--------------------+--------------------+--------------------+
| Primary revenue  | ``8100 00``        | ``8200 00`` /      | ``8400 00``        |
| account          |                    | ``8000 00``        |                    |
+------------------+--------------------+--------------------+--------------------+
| Quarterly report | Turnover           | Turnover + § 19    | Vorsteuer,         |
| focus            |                    | limit warnings     | USt, Zahllast      |
+------------------+--------------------+--------------------+--------------------+

Recommended path while applications are pending
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Set ``DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME = 'exempt'`` (already the default).
2. Book course fees to ``8100 00`` (steuerfreie Umsätze) once the chart is loaded.
3. Run ``vat_quarterly_report`` each quarter for turnover records.
4. When Finanzamt confirms **Kleinunternehmer** or **standard VAT**, update admin
   and run ``sync_tax_regime`` (see below).

Configure the tax profile
~~~~~~~~~~~~~~~~~~~~~~~~~

Django admin → **Entity tax profiles** → your entity:

- **Tax regime** — ``exempt``, ``small_business``, or ``standard``
- **Default VAT rate** — ``0.19`` only for ``standard``; must be ``0`` for the
  other regimes (validated on save)
- **VAT ID** — your USt-IdNr when you have one

After changing regime:

.. code-block:: shell

   python manage.py sync_tax_regime --entity=your-entity-slug

This deactivates accounts that do not belong to the new regime (e.g. hides
``1576 00`` / ``1776 00`` when moving to exempt or Kleinunternehmer).

Daily bookkeeping examples
--------------------------

Use **posted** journal entries (and invoices/bills where you use accrual workflow).
Attach a **supporting document** (Beleg) before post when
``REQUIRE_SUPPORTING_DOCUMENT_ON_POST`` is enabled.

Student pays course fee (bank receipt)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Exempt regime** — gross amount, no VAT lines:

.. code-block:: text

   Debit   1200 00  Bank                    500.00
   Credit  8100 00  Steuerfreie Umsätze     500.00

**Kleinunternehmer** — gross on general revenue:

.. code-block:: text

   Debit   1200 00  Bank                    500.00
   Credit  8200 00  Erlöse                   500.00

**Standard VAT** — if you invoice €500 gross incl. 19% VAT, posting migration
splits automatically on invoice/bill migration:

.. code-block:: text

   Debit   1200 00  Bank                    500.00
   Credit  8400 00  Erlöse (net)            420.17
   Credit  1776 00  Umsatzsteuer               79.83

Pay freelance teacher
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Debit   3100 11  Honorare Schule         800.00
   Credit  1200 00  Bank                     800.00

Rent training room
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Debit   4210 10  Mieten Schulräume       350.00
   Credit  1200 00  Bank                     350.00

Steuerberater invoice
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Debit   4955 00  Buchführungskosten      200.00
   Credit  1600 00  Verbindlichkeiten        200.00

   # When paid:
   Debit   1600 00  Verbindlichkeiten       200.00
   Credit  1200 00  Bank                     200.00

Accreditation fee
~~~~~~~~~~~~~~~~~

.. code-block:: text

   Debit   4390 10  Gebühren                150.00
   Credit  1200 00  Bank                     150.00

Supporting documents (Belegpflicht)
-----------------------------------

Germany defaults to ``REQUIRE_SUPPORTING_DOCUMENT_ON_POST = True``.

Before a journal entry can be **posted**, it must have at least one linked
**Supporting document** (receipt, invoice PDF, bank statement, contract, etc.).

- Model: ``django_ledger_extensions.models.SupportingDocumentModel``
- Managed in Django admin (and via future UI integrations)
- Documents become **immutable** after the journal entry is posted

To disable for local dev only:

.. code-block:: python

   DJANGO_LEDGER_DE_REQUIRE_SUPPORTING_DOCUMENT_ON_POST = False

Quarterly VAT and turnover report
---------------------------------

Purpose
~~~~~~~

One command gives regime-appropriate numbers from **posted** ledger data:

- **Standard** — Vorsteuer, Umsatzsteuer, **Zahllast** (expected ELSTER payment)
- **Kleinunternehmer** — turnover vs § 19 limits (no VAT return)
- **Exempt** — turnover for your records

Commands
~~~~~~~~

.. code-block:: shell

   # Current calendar quarter
   python manage.py vat_quarterly_report --entity=your-entity-slug

   # Specific quarter
   python manage.py vat_quarterly_report --entity=your-entity-slug --year=2026 --quarter=1

   # JSON for spreadsheets / Steuerberater handoff
   python manage.py vat_quarterly_report --entity=your-entity-slug --year=2026 --quarter=1 --json

Example output (standard VAT)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   VAT quarterly report — my-school
   Regime: standard
   Period: Q1 2026 (2026-01-01 – 2026-03-31)

     Vorsteuer (input VAT):           190.00 €
     Umsatzsteuer (output VAT):       380.00 €
     Expected payment (Zahllast):     190.00 €

     Quarter turnover:               2000.00 €
     Year-to-date turnover:          2000.00 €

   USt-Voranmeldung (ELSTER): expected payment ≈ 190.00 € ...

Example output (Kleinunternehmer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Kleinunternehmer (§ 19 UStG): no Umsatzsteuervoranmeldung ...
     Quarter turnover:               5000.00 €
     Year-to-date turnover:         12000.00 €
     Prior-year turnover:           18000.00 €  (limit 22000 €)

Action items appear if YTD or prior-year turnover exceeds configured limits.

When numbers are wrong
~~~~~~~~~~~~~~~~~~~~~~

- **All zeros** — no posted JEs in that quarter, or wrong entity slug
- **No VAT lines (standard)** — regime is not ``standard``, or invoices were not
  migrated/posted through accrual workflow (VAT split runs in ``adjust_posting``)
- **Turnover looks too high/low** — check income-account credits minus debits on
  posted entries

Python API
~~~~~~~~~~

.. code-block:: python

   from django_ledger.models import EntityModel
   from django_ledger_countries.de.vat.reporting import (
       build_vat_quarterly_report,
       format_vat_quarterly_report,
   )

   entity = EntityModel.objects.get(slug='my-school')
   report = build_vat_quarterly_report(entity, year=2026, quarter=1)

   print(report.tax_regime)
   print(report.net_vat_payable)    # standard only
   print(report.quarter_turnover)
   print(report.ytd_turnover)
   print(format_vat_quarterly_report(report))

Invoice footnotes (future templates)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from django_ledger_countries.de import vat

   notice = vat.invoice_vat_notice_for_entity(entity)
   # § 4 UStG text for exempt, § 19 for Kleinunternehmer, empty for standard

Management commands reference
-----------------------------

``sync_skr03``
   Load DATEV SKR03 CSV; apply regime-aware starter activation.

   .. code-block:: shell

      python manage.py sync_skr03 --entity=SLUG [--force] [--activate-all] [--deactivate-all]

``sync_tax_regime``
   Re-apply active starter accounts after changing Entity Tax Profile.

   .. code-block:: shell

      python manage.py sync_tax_regime --entity=SLUG

``vat_quarterly_report``
   Quarterly VAT or turnover summary from posted transactions.

   .. code-block:: shell

      python manage.py vat_quarterly_report --entity=SLUG [--year=Y] [--quarter=1-4] [--json]

Settings reference
------------------

All resolve via ``get_ledger_setting()`` (country-specific → global → plugin
default). See :doc:`regional` for resolution order.

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Django setting
     - DE default
     - Purpose
   * - ``DJANGO_LEDGER_COUNTRY``
     - ``us`` (set ``de``)
     - Active country plugin
   * - ``DJANGO_LEDGER_DE_DEFAULT_COA``
     - ``skr03``
     - Chart loader
   * - ``DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME``
     - ``exempt``
     - New entity tax profile
   * - ``DJANGO_LEDGER_DE_DEFAULT_VAT_RATE``
     - ``0.19``
     - Standard regime only
   * - ``DJANGO_LEDGER_DE_KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT``
     - ``22000``
     - Quarterly report warning
   * - ``DJANGO_LEDGER_DE_KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT``
     - ``50000``
     - Quarterly report warning
   * - ``DJANGO_LEDGER_DE_SKR03_CSV``
     - bundled CSV
     - Alternate DATEV export path
   * - ``DJANGO_LEDGER_DE_SKR03_STARTER_CODES``
     - built-in list
     - Override active accounts
   * - ``DJANGO_LEDGER_DE_REQUIRE_SUPPORTING_DOCUMENT_ON_POST``
     - ``True``
     - Beleg before JE post

End-to-end checklist
--------------------

**First-time setup**

#. ``DJANGO_LEDGER_COUNTRY = 'de'`` and regional apps in ``INSTALLED_APPS``
#. ``python manage.py migrate``
#. Create entity in ledger UI
#. ``python manage.py sync_skr03 --entity=your-slug``
#. Confirm **Entity tax profile** regime in Django admin
#. Activate any extra accounts you need in chart of accounts UI

**Each month**

#. Enter invoices, bills, and bank transactions
#. Attach supporting documents
#. Post journal entries

**Each quarter**

#. ``python manage.py vat_quarterly_report --entity=your-slug``
#. Hand Zahllast or turnover figures to Steuerberater / ELSTER as applicable

**When tax status changes**

#. Update **Entity tax profile → tax regime**
#. ``python manage.py sync_tax_regime --entity=your-slug``
#. Point course-fee items at the correct revenue account (``8100`` / ``8200`` / ``8400``)

FAQ
---

**Do I need all 2,700 accounts active?**
   No. Use the starter set; activate more only when needed.

**Can I be exempt and Kleinunternehmer at the same time?**
   Pick one **regime** in software that matches your primary legal status; your
   Steuerberater decides what applies. The profile stores a single regime.

**Why does standard VAT show zero Vorsteuer/USt?**
   Usually means no posted activity on VAT clearing accounts (``1576 00`` /
   ``1776 00``) — often because regime is not ``standard`` or amounts were booked
   manually without going through invoice/bill VAT split.

**Does this file USt-Voranmeldung to ELSTER?**
   No. It summarizes ledger data. ELSTER filing is separate.

**Where is the architecture documented?**
   :doc:`regional`
