German School / Bildungsurlaub How-To
=====================================

This guide is for **German training providers** using django-ledger with the
``de`` country plugin — especially **Bildungsurlaub-accredited courses** (online
and in-person), freelance teachers, venue rental, and a small active account set
on top of the full **DATEV SKR03** chart.

It covers setup, daily bookkeeping, tax regimes, quarterly reporting, and
**step-by-step workflows for real invoices** (student fees, supplier bills,
Belege). For architecture and plugin internals, see :doc:`regional`.

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

Beleg inbox (staging before you know the ledger object)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not every receipt arrives with an invoice or journal entry UUID. Use the
**document inbox** to stage photos, PDFs, or email attachments first and link
them later.

Model: ``django_ledger_extensions.models.DocumentInboxItem``

Python API:

.. code-block:: python

   from decimal import Decimal
   from django_ledger_extensions.documents import create_inbox_item, link_inbox_item_to_object

   inbox = create_inbox_item(
       entity,
       uploaded_file,
       description='Freelancer invoice May',
       suggested_amount=Decimal('800.00'),
       external_source='email',
       external_id='msg-12345',  # optional idempotency for connectors
   )

   # Later, when you have the target:
   link_inbox_item_to_object(inbox, journal_entry)  # or invoice / bill

Management command:

.. code-block:: bash

   python manage.py link_beleg --inbox=<uuid> --invoice=<uuid>
   python manage.py link_beleg --inbox=<uuid> --journal-entry=<uuid>

One-step manual expense with photo:

.. code-block:: python

   from django_ledger_extensions.documents import create_quick_expense

   je, doc = create_quick_expense(
       entity,
       amount=Decimal('25.00'),
       expense_account=expense_account,
       description='Office supplies',
       file=uploaded_file,
   )

Import course payments from your class webapp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Payments from your class registration webapp (or any future connector) can
create a **draft invoice** without tying the ledger to Stripe or another
processor. The connector name is just a string (``class_webapp``, ``stripe``,
``paypal``, …).

Stable import API:

.. code-block:: python

   from decimal import Decimal
   from django.utils import timezone
   from django_ledger_extensions.payments import ExternalPaymentPayload, import_external_payment

   record = import_external_payment(entity, ExternalPaymentPayload(
       provider='class_webapp',
       external_id='pay_123',          # unique per provider + entity
       amount=Decimal('490.00'),
       paid_at=timezone.now(),
       customer_email='student@example.com',
       customer_name='Alex Student',
       product_name='Bildungsurlaub course',
       description='May 2026 cohort',
       receipt_file=uploaded_file,     # optional
   ))
   draft_invoice = record.invoice

Re-running the same ``provider`` + ``external_id`` is **idempotent** — you get
the same ``ExternalPaymentRecord`` and draft invoice back.

CLI for manual testing:

.. code-block:: bash

   python manage.py import_external_payment \\
     --entity=your-entity-slug \\
     --provider=class_webapp \\
     --external-id=pay_123 \\
     --amount=490.00 \\
     --paid-at=2026-05-25T14:30:00 \\
     --customer-email=student@example.com \\
     --receipt=/path/to/receipt.pdf

After import, review the draft invoice, attach any missing Beleg, then approve
and post through your normal workflow. Germany validation accepts a supporting
document on the **invoice** as well as on the journal entry.

When you have real invoices (workflows)
---------------------------------------

Use this section when you start booking **real** student fees and **real**
supplier paperwork — not test data. It ties together the ledger UI, Belege, and
(class webapp) payment import.

Three document types you will handle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+------------------+---------------------------+-------------------------------+
| Direction        | What it is                | Ledger object                 |
+==================+===========================+===============================+
| **Outgoing**     | Invoice **you send**      | **Invoice** (student course   |
|                  | to a student              | fee)                          |
+------------------+---------------------------+-------------------------------+
| **Incoming**     | Invoice **you receive**   | **Bill** (Steuerberater,      |
|                  | from a supplier           | freelancer, rent, …)           |
+------------------+---------------------------+-------------------------------+
| **Small receipt**| Photo/PDF without a       | **Journal entry** via         |
|                  | formal bill               | ``create_quick_expense``      |
+------------------+---------------------------+-------------------------------+

**Golden rule (Germany):** before any journal entry **posts**, there must be a
supporting document on the **journal entry** *or* on the wrapped **invoice/bill**
on the same ledger. Attach the PDF or payment receipt **before** you click
*Approve* / *Mark as paid* / *Post*.

Outgoing: student paid via your class webapp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typical case: the student already paid online; your webapp creates a **draft
invoice** in the ledger.

**1. Import (automatic from webapp, or manual once for testing)**

.. code-block:: python

   record = import_external_payment(entity, ExternalPaymentPayload(...))
   invoice = record.invoice   # status: draft

Or via CLI:

.. code-block:: shell

   python manage.py import_external_payment \\
     --entity=your-entity-slug \\
     --provider=class_webapp \\
     --external-id=<payment-id-from-webapp> \\
     --amount=490.00 \\
     --paid-at=2026-05-25T14:30:00 \\
     --customer-email=student@example.com \\
     --receipt=/path/to/payment-receipt.pdf

**2. Review the draft** (ledger UI → Invoices)

- Customer name and email correct?
- Line item (course name) and **amount** match what was charged?
- Draft date reasonable?
- If you did **not** pass ``receipt_file``, attach the payment receipt now
  (Django admin → supporting documents on the invoice, or ``link_beleg`` from
  inbox).

**3. Approve the invoice**

- In the invoice detail view: **Mark as approved**.
- On accrual entities this creates the revenue / receivable journal entry and
  **posts the ledger**.
- The Beleg on the **invoice** satisfies Germany's pre-post check.

**4. Mark as paid**

- The money is already in your bank, so: **Mark as paid** with the **actual
  payment date** (same day the webapp recorded payment).
- This books bank ↔ receivable and locks the invoice ledger.

**5. Quarterly report**

- Only **posted** amounts count. After step 3–4, run
  ``vat_quarterly_report`` at quarter-end.

.. note::

   Re-importing the same ``provider`` + ``external_id`` is safe — you get the
   same draft invoice back, not a duplicate.

Outgoing: student invoice before payment (manual)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use when you invoice first and the bank transfer arrives days later.

#. **Create invoice** in the ledger UI (customer, course line item, amount).
#. **Attach** your sent invoice PDF (or quote) as supporting document on the
   invoice.
#. **Mark as approved** when you send it to the student.
#. When payment hits the bank: **Mark as paid** with payment date.
#. If the bank receipt was not attached earlier, stage it in the **Beleg inbox**
   and ``link_beleg`` to the invoice **before** marking paid (or attach to the
   payment journal entry once created).

Incoming: supplier invoice (Bill)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Steuerberater, freelance teachers (with invoice), venue rent, etc.

#. **Save the PDF** — either upload to **Beleg inbox** (email/camera) or keep
   the file ready.
#. **Create a Bill** in the ledger UI: vendor, amount, expense account
   (e.g. ``4955 00`` Steuerberater, ``3100 11`` Honorare, ``4210 10`` Miete).
#. **Link the Beleg** to the bill:

   .. code-block:: shell

      python manage.py link_beleg --inbox=<inbox-uuid> --bill=<bill-uuid>

   Or attach via Django admin → supporting documents.

#. **Mark as approved** — posts expense and accounts payable (plus VAT split if
   ``standard`` regime).
#. **Mark as paid** when you pay from the bank (attach bank transfer receipt if
   not already on the bill or payment entry).

Small expense without a formal bill
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Coffee, stationery, a simple receipt — no supplier invoice:

.. code-block:: python

   je, doc = create_quick_expense(
       entity,
       amount=Decimal('25.00'),
       expense_account=expense_account,  # e.g. 4980 10 IT consumables
       description='Office supplies',
       file=receipt_photo,
   )

Then open the journal entry in the UI, check accounts, and **post**. The Beleg
is already on the JE.

Beleg checklist (print this mentally)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+-------------------------------+----------------------------------------------+
| Situation                     | Attach Beleg to…                             |
+===============================+==============================================+
| Class webapp payment import   | Invoice (auto if ``receipt_file`` passed)    |
| Manual student invoice        | Invoice (your PDF) + bank receipt when paid  |
| Supplier bill                 | Bill (their invoice PDF)                     |
| Quick expense                 | Journal entry (done by ``create_quick_expense``) |
| Staged email/camera photo     | Inbox first → ``link_beleg`` when you know   |
|                               | invoice / bill / JE UUID                     |
+-------------------------------+----------------------------------------------+

Invoice / bill status flow (ledger UI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Student invoice (outgoing)**

.. code-block:: text

   draft  →  [review]  →  approved  →  paid
              ↑              ↑            ↑
         webapp import   books revenue   books bank;
         or manual       + receivable    locks ledger

**Supplier bill (incoming)**

.. code-block:: text

   draft  →  approved  →  paid
              ↑            ↑
         books expense   clears AP +
         + AP            bank payment

Do **not** skip **approved** before **paid** on accrual entities — that is
when the main ledger entries are created.

Where to find things in Django admin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Entity tax profiles** — regime (exempt / Kleinunternehmer / standard)
- **Document inbox items** — unlinked receipts waiting for ``link_beleg``
- **External payment records** — webapp imports; links to draft invoice
- **Supporting documents** — files attached to invoices, bills, JEs

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

``link_beleg``
   Link a staged inbox item to an invoice, bill, or journal entry.

   .. code-block:: shell

      python manage.py link_beleg --inbox=INBOX_UUID --invoice=INVOICE_UUID
      python manage.py link_beleg --inbox=INBOX_UUID --bill=BILL_UUID
      python manage.py link_beleg --inbox=INBOX_UUID --journal-entry=JE_UUID

``import_external_payment``
   Create a draft invoice from an external payment (class webapp, webhook test, …).

   .. code-block:: shell

      python manage.py import_external_payment \\
        --entity=SLUG --provider=class_webapp --external-id=PAY_ID \\
        --amount=490.00 --paid-at=2026-05-25T14:30:00 \\
        [--customer-email=...] [--receipt=/path/to/file.pdf]

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

**Each month (real invoices)**

#. **Student fees:** import from class webapp (or create invoice manually) →
   review draft → Beleg on invoice → **Approve** → **Mark as paid**
#. **Supplier costs:** inbox PDF → create **Bill** → ``link_beleg`` → **Approve**
   → **Mark as paid** when bank payment goes out
#. **Small receipts:** ``create_quick_expense`` + post JE
#. Confirm nothing is stuck in **draft** with missing Belege before quarter-end

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

**Student paid in the webapp — what do I click in the ledger?**
   Open the **draft invoice** → check amount/customer → ensure payment receipt
   is attached → **Mark as approved** → **Mark as paid** (with payment date).
   See *When you have real invoices* above.

**I have a PDF from my Steuerberater — what now?**
   Upload to inbox (or admin) → create a **Bill** → ``link_beleg`` → approve →
   pay when you transfer the money.

**Where is the architecture documented?**
   :doc:`regional`
