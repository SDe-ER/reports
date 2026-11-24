---
title: KSA VAT Return
description: The Saudi VAT return, fields 1 to 16, with amount, adjustment and VAT columns.
sidebar:
  order: 1
---

**KSA VAT Return** lays out the Saudi VAT return as fields 1 to 16, with three columns: **Amount**, **Adjustment**
and **VAT Amount**. Open it from the **Sijill** page (apps screen or desktop icon, then the sidebar), or type its name in the search bar.

## Filters

| Filter | Notes |
|---|---|
| Company | A company in Saudi Arabia with [KSA VAT Settings](/reports/getting-started/configuration/). |
| From Date, To Date | Default: the current quarter. |

## Fields

| No | Field | How it is filled |
|---|---|---|
| | Standard rated sales at 15% / 5% | One line per rate charged on sales. |
| 1 | Standard rated sales | Sales charged at a positive rate on an Output VAT account. |
| 2 | Sales to citizens (private healthcare / education) | Not calculated. |
| 3 | Zero rated domestic sales | Sales with a 0% VAT row, to a customer in the company's country or without an address country. |
| 4 | Exports | Sales with a 0% VAT row, to a customer whose address country is another country. |
| 5 | Exempt sales | Not calculated, shows zero. |
| 6 | Total sales | Fields 1, 3 and 4. |
| | Standard rated purchases at 15% / 5% | One line per rate paid on purchases. |
| 7 | Standard rated domestic purchases | Purchases with VAT on an Input VAT account. |
| 8 | Imports, VAT paid at customs | Not calculated. |
| 9 | Imports, reverse charge | Not calculated. |
| 10 | Zero rated purchases | Purchases with a 0% VAT row. |
| 11 | Exempt purchases | Not calculated, shows zero. |
| 12 | Total purchases | Fields 7 and 10. |
| 13 | Total VAT due for the current period | VAT of field 6 less VAT of field 12. |
| 14 | Corrections from previous periods | Not calculated, shows zero. |
| 15 | VAT credit carried forward | Not calculated, shows zero. |
| 16 | Net VAT due (or claim) | Field 13 plus fields 14 and 15. A negative value is a claim. |

## Where the amounts come from

- **Sales and Purchase Invoices** (submitted): the taxable amount and VAT of each item from the invoice's item tax
  details, for tax rows on an Output VAT (sales) or Input VAT (purchases) account. Purchase tax rows that are
  deducted, or only added to valuation, are not counted.
- **Credit notes, debit notes and purchase returns** go to the **Adjustment** column. The VAT column includes them.
- **Other vouchers** (Journal Entry, Payment Entry, ...) that post to an Output or Input VAT account: VAT from the
  general ledger, taxable amount from the account's tax rate. A reduction of output or input VAT goes to the
  Adjustment column.

## What is not reported

- **Opening entries.**
- **Entries that only move amounts between the VAT accounts** in KSA VAT Settings: closing a return into the VAT
  Settlement account, paying it, reclassifications between VAT accounts. These are not taxable transactions.

Both are listed in the report **VAT Documents Requiring Completion** with the status **Not reported** when
**Include settlement and opening entries** is ticked, so every movement on the VAT accounts can be traced.

## Data rules

The return is built from invoices. The rules start on the date set in
[KSA VAT Settings](/reports/getting-started/configuration/) (**Output VAT from Sales Invoices only, from date**). When
the date is empty the rules apply to every date. Lines before the date are never left out; missing data is only
listed with the status **Included (warning)**.

Vouchers that need attention are listed in **VAT Documents Requiring Completion**, one row per voucher, with the failed
rules in English and Arabic.

**Sales (from the date on).** Output VAT is counted only from Sales Invoices, including credit and debit notes. Any
other voucher with output VAT, for example a Journal Entry, is left out of the return and the detail and listed with
the status **Excluded** and the code `OUTPUT_VAT_BY_JOURNAL_ENTRY`. A Sales Invoice is never left out: missing customer
name, VAT number or other ID is only reported, with the status **Included (warning)**.

**Purchases (from the date on).** Input VAT is counted only from Purchase Invoices and Journal Entries; any other
voucher is left out (`INPUT_VAT_SOURCE_NOT_ALLOWED`). A voucher that fails any of these rules is left out of the return
and of the detail report and listed with the status **Excluded**:

- **a.** A supplier is set and has a name (`SUPPLIER_MISSING`).
- **b.** The supplier invoice number is present and not used on another voucher of the same supplier
  (`BILL_NO_MISSING`, `BILL_NO_DUPLICATE`).
- **c.** The supplier VAT number is valid: 15 digits, starting and ending with 3 (`SUPPLIER_VAT_INVALID`).
- **d.** The check **Buyer details verified on supplier invoice** is ticked: the supplier invoice shows the full name,
  VAT number and address of the company (`BUYER_DETAILS_NOT_VERIFIED`).

A missing attachment (`ATTACHMENT_MISSING`) is only a warning: the voucher is counted and listed as
**Included (warning)**. A voucher that reduces input VAT follows the same rules. When it is excluded it also gets
`REDUCTION_EXCLUDED`, because excluding it increases the VAT claim. Complete its data so it is counted again.

**Statuses.** Excluded, Included (warning), Not reported.

**Adjustment column.** It holds credit notes, debit notes, purchase returns and purchase Journal Entries that reduce
input VAT.

## Open the transactions behind an amount

Every amount in a field with transactions is a link. It opens **KSA VAT Return Detail** with the same company and
dates, filtered to that field and rate.

## Print

**Menu → Print** gives an A4 page: company name, VAT registration number (from the Company's Tax ID), the period,
and the return fields, with section bands and bold totals as on the official form. The print follows the user's
language: right to left in Arabic.

:::caution[Before you file]
Input VAT is reported as booked. The report does not decide whether it can be recovered: review the supplier
invoice numbers and tax IDs in the detail report first. The app is not certified by ZATCA.
:::
