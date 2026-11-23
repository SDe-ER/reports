# Changelog

All notable changes to Sijill are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- KSA VAT Return print: the table header is #f3f3f3 and the table text #171717 (section-heading rows and the No column included),
  with the grey heading/total row fills and #d1d8dd borders, also when the site Print Style sets other colours with
  `!important` (rules scoped to the report's own classes; the site Print Style and Letter Heads
  are not changed). The label / value block no longer repeats the company, which stays on the line above the title.
  A test checks the colours, the scoping and the block.

## [0.1.2] - 2026-11-23

### Added
- **Sijill workspace**: a page of its own named Sijill (سِجِلّ) with the two VAT reports and KSA VAT Settings, a
  sidebar, an apps-screen entry and a desktop icon. Every new report is added to it; a test checks the sidebar lists
  every Sijill report.

### Changed
- KSA VAT Return print follows the standard print layout: small company line, title over a grey rule, a
  label / value block (company, VAT registration number, period, issue date), bordered grey table with section and
  total rows, and Prepared / Reviewed / Approved signature lines. The site Letter Head adds the logo, header and footer.
- `app_logo_url` removed from hooks so the app never replaces the site's own navbar / login logo.

## [0.1.1] - 2026-11-23

### Fixed
- VAT that a bank charges on its fees (Dr Input VAT, Cr Bank) is reported in field 7 again. Only entries that
  reduce a VAT account against bank or cash (paying the authority, receiving a refund) are excluded as settlements.
- The Arabic catalogue no longer re-translates strings that Frappe, ERPNext or HRMS already translate (for
  example "No", "Amount", "Voucher No"). Report-specific wording uses the translation context
  "KSA VAT Return", so the rest of the site keeps its own Arabic labels. A test blocks such overrides.
  "VAT Amount" and "VAT Registration Number" (translated by ksa_compliance) use the same context; the test now
  checks every installed app. (This fix is already in the v0.1.0 tag; the 0.1.0 notes did not list it.)

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

[Unreleased]: https://github.com/SDe-ER/reports/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/SDe-ER/reports/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SDe-ER/reports/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SDe-ER/reports/releases/tag/v0.1.0
