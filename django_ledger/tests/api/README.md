# High-Level API Behavior Tests

This directory contains deterministic, high-level behavior tests for Django Ledger's public model API.

The goal of this test suite is not to replace the existing test suite, reorganize project testing strategy, or prescribe a different testing philosophy. Instead, it adds an isolated and readable layer of contract-style tests around the public APIs that downstream applications are likely to depend on.

These tests were added as a human-reviewed, AI-assisted contribution using OpenAI GPT-5.5. The intent is to be transparent about the development process while keeping responsibility, review, and final judgment with the human contributor.

## Why this directory exists

Django Ledger exposes a rich programming API through its models, managers, querysets, and domain methods. Many important behaviors are not merely field-level behaviors; they involve coordinated model interactions such as:

* entity-scoped number generation,
* fiscal-year-scoped document numbering,
* entity-unit-scoped journal entry sequencing,
* ledger and journal entry posting behavior,
* item transaction ownership across documents,
* import job staging and migration behavior,
* receipt generation from staged transactions,
* closing entry migration into locked journal entries,
* queryset and manager-level filtering contracts.

This directory focuses on those higher-level behaviors.

The tests are intentionally placed under `django_ledger/tests/api/` to keep them separate from the existing test modules. This makes the scope explicit: these are public API behavior tests, not internal implementation tests.

## Design goals

The test suite follows a few guiding principles:

1. **Deterministic setup**

   Tests avoid randomized fixture generation. Each test creates the minimum entity, chart of accounts, accounts, counterparties, items, documents, or staged transactions needed to express the behavior under test.

2. **Public API first**

   Tests prefer public model methods, manager methods, queryset methods, and documented high-level flows over implementation details.

3. **Behavior over implementation**

   The tests assert externally meaningful contracts such as generated numbers, state transitions, ownership links, ledger effects, and queryset results.

4. **Refactor safety**

   The suite is designed to provide confidence before larger model refactors, including possible swappable-model work. If concrete models, abstract bases, foreign keys, or manager implementations change, these tests should help confirm that public behavior remains stable.

5. **Small focused tests**

   Each test tries to verify one business-level invariant. Shared helpers are kept local to each file so individual test modules remain readable in isolation.

## Current coverage

At the time this README was written, the high-level API suite contains 160 passing tests.

The suite covers the following areas.

### Core accounting

* `EntityModel`
* `EntityStateModel`
* `EntityUnitModel`
* `ChartOfAccountModel`
* `AccountModel`
* `LedgerModel`
* `JournalEntryModel`
* `TransactionModel`
* `IOBluePrint` / IO commit behavior

Covered contracts include:

* entity creation,
* default chart of accounts behavior,
* account creation and role defaults,
* ledger and journal entry creation,
* balanced transaction behavior,
* IO blueprint dispatch and commit behavior,
* journal entry number generation,
* entity-unit-scoped journal entry state sequencing.

### Commercial foundation

* `CustomerModel`
* `VendorModel`
* `UnitOfMeasureModel`
* `ItemModel`
* `ItemTransactionModel`
* `BankAccountModel`
* `ReceiptModel`

Covered contracts include:

* customer and vendor creation,
* active, inactive, hidden, and visible queryset behavior,
* unit of measure creation,
* service, product, inventory, and expense item creation,
* item transaction ownership across documents,
* bank account configuration and entity scoping,
* sales, expense, transfer, and refund receipt behavior,
* receipt number generation via `EntityStateModel.KEY_RECEIPT`.

### Documents

* `BillModel`
* `InvoiceModel`
* `EstimateModel`
* `PurchaseOrderModel`
* `ClosingEntryModel`
* `ClosingEntryTransactionModel`

Covered contracts include:

* document configuration,
* draft, review, approved, paid, completed, and fulfilled state behavior where applicable,
* document amount aggregation from item transactions,
* entity-scoped and fiscal-year-scoped document numbering,
* purchase order fulfillment guard rails,
* closing entry posting and unposting,
* locked closing journal entry generation,
* balanced closing entry validation,
* closing entry transaction normalization.

### Import and staging

* `ImportJobModel`
* `StagedTransactionModel`

Covered contracts include:

* import job configuration and ledger creation,
* import job entity scoping,
* pending/imported annotation behavior,
* staged transaction filtering by entity and import job,
* staged transaction splitting,
* parent/child staged transaction behavior,
* customer/vendor mutual exclusion,
* staged transaction readiness for import,
* non-receipt staged transaction migration into journal entries,
* receipt staged transaction migration into `ReceiptModel` and posted journal entries.

### QuerySet and manager contracts

The suite includes explicit coverage for public queryset and manager APIs such as:

* `for_entity(...)`
* `for_user(...)`
* `active()`
* `inactive()`
* `hidden()`
* `visible()`
* `draft()`
* `approved()`
* `paid()`
* `posted()`
* `not_posted()`
* `services()`
* `products()`
* `expenses()`
* `inventory_all()`
* `contracts()`
* `estimates()`
* `for_customer(...)`
* `for_vendor(...)`
* `for_dates(...)`
* `for_import_job(...)`

These contracts are important because downstream code often depends on queryset behavior as much as direct model methods.

## Known observations captured by the suite

The test suite intentionally documents some non-obvious current behaviors.

### Entity state scoping

`EntityStateModel` sequences are scoped by:

```text
entity_model + entity_unit + fiscal_year + key
```

Customer, vendor, and item numbering use entity-level state without fiscal year or entity unit.

Bills, invoices, estimates, purchase orders, receipts, and journal entries use fiscal-year-scoped state.

Journal entries additionally use `entity_unit` when present.

### EntityUnitModel creation

`EntityUnitModel` is based on Treebeard `MP_Node`. It should be created through Treebeard APIs such as `add_root(...)`, not by plain `Model(...).save()` construction.

### ClosingEntry behavior

Posting a balanced closing entry creates locked and posted journal entries under the closing entry ledger. Unposting removes those generated journal entries and transactions.

Closing entries cannot be posted with future timestamps because the generated journal entries are validated as posted journal entries.

### StagedTransaction annotation dependency

Some staged transaction operations, such as `add_split()`, expect annotation-backed fields like `children_count`. Tests use annotated queryset instances when exercising those behaviors.

### Current upstream issue surfaced by tests

`ClosingEntryTransactionModel.objects.for_entity(...)` currently exposes an apparent bug: it calls `lazy_loader.get_entity(...)`, but that method is not available on the lazy loader. The test suite documents this current behavior explicitly instead of hiding it.

This can be addressed separately with a focused regression test and fix.

## Running the suite

Run all high-level API behavior tests:

```bash
python manage.py test django_ledger.tests.api
```

Run an individual module:

```bash
python manage.py test django_ledger.tests.api.test_receipt_api
python manage.py test django_ledger.tests.api.test_data_import_api
python manage.py test django_ledger.tests.api.test_closing_entry_api
```

## Contribution notes

These tests are intentionally verbose in setup. The verbosity is a tradeoff: it keeps each test module understandable without relying on hidden randomized fixtures or broad shared test state.

The suite is intended to support future refactors by making current public behavior explicit. It should be especially useful before changes involving:

* abstract/concrete model boundaries,
* swappable model support,
* manager/queryset refactors,
* foreign key target changes,
* document lifecycle changes,
* ledger posting internals,
* entity state and numbering internals.

## AI assistance disclosure

This test suite was developed with AI assistance from OpenAI GPT-5.5 and reviewed by a human contributor.

The AI system helped draft test structures, identify likely behavior contracts, and iterate on failures. The human contributor ran the tests, inspected failures, reviewed behavior against the source code, and decided which contracts should be preserved.

The contribution should therefore be understood as human-owned and human-reviewed, with AI used as a development aid.
