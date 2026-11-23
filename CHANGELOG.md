# Changelog

All notable changes to Sijill are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- The Arabic catalogue no longer re-translates strings that Frappe, ERPNext or HRMS already translate (for
  example "No", "Amount", "Voucher No"). Report-specific wording uses the translation context
  "KSA VAT Return", so the rest of the site keeps its own Arabic labels. A test blocks such overrides.
  "VAT Amount" and "VAT Registration Number" (translated by ksa_compliance) use the same context; the test now
  checks every installed app.

## [0.1.0] - 2026-11-23

### Added
- **KSA VAT Return**: the Saudi VAT return, fields 1 to 16, with Amount, Adjustment and VAT Amount columns, links
  from every amount to its transactions, and an A4 print view.
- **KSA VAT Return Detail**: the vouchers behind every amount (voucher, supplier / customer invoice number, party,
  tax ID, taxable amount, VAT, total including VAT, VAT account), with Excel / PDF export and "Show Excluded
  Entries".
- **KSA VAT Settings**: per company Output VAT, Input VAT and VAT Settlement accounts.
- Arabic translation of every label.
- Documentation site in English and Arabic: https://sde-er.github.io/reports/

### Fixed
- VAT payments and refunds booked through a VAT account against a bank or cash account are not reported as sales
  or purchase adjustments.
- A VAT journal entry on a VAT account without a Tax Rate stays in the standard rated field.

### Impact
- New DocTypes `KSA VAT Settings` and `KSA VAT Account`, two new reports. Read only: no change to existing
  documents, ledger entries or permissions.
- Rollback: `bench --site <site> uninstall-app sijill` removes the reports and settings only.

[Unreleased]: https://github.com/SDe-ER/reports/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SDe-ER/reports/releases/tag/v0.1.0
