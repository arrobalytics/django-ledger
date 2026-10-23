## Summary

<!-- What problem does this solve, and why is this change needed? Focus on the "why". -->

## Related issue

<!-- Link the issue this closes or relates to, e.g. Closes #123 -->

- Closes #

## Change type

<!-- Check all that apply -->

- [ ] Bug fix (double-entry, statements, documents, imports, etc.)
- [ ] New feature / enhancement
- [ ] Breaking change (public API, model fields, or behavior)
- [ ] Database migration
- [ ] Documentation / examples / notebooks only
- [ ] Tests only
- [ ] Performance / refactor with behavioral parity

## Affected areas

<!-- Check all that apply -->

- [ ] Entity / multi-tenancy
- [ ] Chart of Accounts / AccountModel
- [ ] Ledgers / Journal Entries / Transactions
- [ ] Bills / Invoices / Receipts / POs / Estimates
- [ ] Customers / Vendors
- [ ] Financial statements / ratios / IO digest
- [ ] Closing entries / fiscal periods
- [ ] Inventory / Items / UoM
- [ ] Bank accounts / OFX & QFX import
- [ ] Admin / UI / templates / forms / views
- [ ] Settings / management commands
- [ ] Docs / notebooks

## Accounting & integrity notes

<!-- Required when touching ledgers, JEs, transactions, statements, closing, or imports -->

- Does this preserve balanced journal entries? 
- Any impact on historical statements or posted documents?
- Migration / data backfill needed for existing entities?

## How to test

<!-- Steps maintainers can follow. Prefer concrete Entity / CoA / document scenarios. -->

1.
2.
3.

## Checklist

- [ ] PR targets the `dev` branch
- [ ] I have read and agree to the [Contributor License Agreement](https://github.com/arrobalytics/django-ledger/blob/dev/Contribute.md) in `Contribute.md`
- [ ] Tests added or updated for new behavior / bug fixes (when practical)
- [ ] Docs / docstrings updated if public API or user-facing behavior changed
- [ ] No secrets, credentials, or local `.env` data included
- [ ] Cosmetics-only / lint-only changes avoided unless they fix a real defect

## Screenshots / sample output

<!-- UI changes, statement output, or sample digests — optional -->
