# Changelog

All notable changes to Sijill are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.5] - 2026-11-24

### Added
- KSA VAT Settings: the date field "Output VAT from Sales Invoices only, from date". Empty: the rules are off and
  the return works as in earlier versions. From that date the KSA VAT Return is built from invoices. Output VAT is counted only from Sales Invoices (also credit and
  debit notes); another voucher with output VAT is left out and listed with the code
  OUTPUT_VAT_BY_JOURNAL_ENTRY (Journal Entry) or OUTPUT_VAT_SOURCE_NOT_ALLOWED, plus OUTPUT_REDUCTION_EXCLUDED when it
  reduces output VAT. Input VAT is counted only from Purchase Invoices and Journal Entries
  (INPUT_VAT_SOURCE_NOT_ALLOWED for other vouchers) that pass four rules: a supplier with a name, a real supplier invoice
  number (not empty, not a placeholder such as 0, - or N/A, not the voucher number) that is not used twice by the same
  supplier (compared without case and spaces; every copy is excluded; Journal Entries count only when they debit input
  VAT; Purchase Invoice returns are exempt from the duplicate check), a valid supplier VAT number (15 digits, starts and ends with 3)
  and the new check "Buyer details verified on supplier invoice". A missing attachment is only a warning. An excluded
  voucher that reduces input VAT also gets REDUCTION_EXCLUDED. Before the date nothing is left out; missing data is
  only listed as "Included (warning)".
- Report "VAT Documents Requiring Completion": one row per voucher that is excluded, warned about or (optionally) not
  reported, with the failed rules in English and Arabic and a link to the voucher.
- Custom Field "Buyer details verified on supplier invoice" on Purchase Invoice and Journal Entry (fixture).

### Changed
- KSA VAT Return Detail lists only the vouchers counted in the return, with invoice number, party name and tax ID on
  every row (a marker where data is missing). The filter "Show Excluded Entries" is removed; a button opens the new
  report.

## [0.1.4] - 2026-11-24

### Fixed
- KSA VAT Return field 14 label: corrections from previous periods "between SAR ±15,000" (was ±5,000), per ZATCA
  "Guideline for Tax Invoicing and Records under VAT Provisions", Version 3 (May 2026), section 10.4 and Implementing
  Regulations Article 63.
- KSA VAT Return Detail: a Journal Entry linked to a Bank Account shows the Bank's name; 0.1.3 showed the Bank Account's
  account holder (the company).

## [0.1.3] - 2026-11-24

### Fixed
- Invoices whose VAT row is an "Actual" amount (Item Wise Tax Detail stores rate 0) are reported as standard rated at
  the VAT account's Tax Rate (or the rate implied by the amounts, snapped to 15% / 5% within 0.5 points) instead of
  zero rated: their amounts move from field 10 (or 3) to field 7 (or 1). Fields 12, 13 and 16 do not change. A line is
  zero rated only when it carries no VAT. An item is counted once per effective rate, also when it has a rate row and an
  "Actual" row on the VAT accounts.
- KSA VAT Return Detail: a Journal Entry without a customer or supplier shows the Bank Account name, else the name of its
  bank or cash account, as party name; no tax ID is shown for it.
- Reclassification Journal Entries (Dr Output VAT / Cr revenue; Dr expense / Cr Input VAT) net against the original
  entry in the return; a test covers it.

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

[Unreleased]: https://github.com/SDe-ER/reports/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/SDe-ER/reports/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/SDe-ER/reports/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/SDe-ER/reports/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SDe-ER/reports/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SDe-ER/reports/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SDe-ER/reports/releases/tag/v0.1.0
