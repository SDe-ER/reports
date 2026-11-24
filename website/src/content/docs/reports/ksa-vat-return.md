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

Every voucher behind the return is checked for the data a VAT return needs. Vouchers that need attention are listed
in **VAT Documents Requiring Completion**, one row per voucher, with the failed rules in English and Arabic.

**Purchases.** A purchase voucher that fails any rule is left out of the return and of the detail report (status
**Excluded**). Input VAT is deducted only with a valid tax invoice in hand; when the missing data is completed, the
voucher is counted again. The rules:

- The supplier invoice number is present and is not used on another voucher of the same supplier (only for voucher
  types that have such a field).
- The supplier name is present.
- The supplier VAT number is valid: 15 digits, starting and ending with 3.
- The check **Buyer details verified on supplier invoice** is ticked (Purchase Invoice and Journal Entry): the
  supplier invoice shows the full name, VAT number and address of the company.
- A file is attached to the voucher (for example a copy of the supplier invoice).

A voucher that **reduces** input VAT is never left out, because leaving it out would increase the VAT claim. It
stays in the return with the status **Included (warning)** and the code `REDUCTION_KEPT`. Complete its data.

**Sales.** A sale is never left out: VAT is due on every taxable sale. Missing customer name, VAT number or other ID
is only reported, with the status **Included (warning)**.

**Statuses.** Excluded, Included (warning), Not reported, Reclassified.

**Reclassification pairs.** A Journal Entry that reverses the VAT of an earlier Journal Entry names it in the field
**Reclassification Of**. When the VAT reverses fully on every VAT account, and the original and all its
reclassification entries are inside the report period, both leave the Amount and Adjustment columns and the detail,
and are listed with the status **Reclassified**. In all other cases (partial reversal, entries in another period,
chains) nothing is removed and the entries are flagged `RECLASS_PARTIAL` or `RECLASS_OTHER_PERIOD` for review. The
Adjustment column then holds only credit notes, debit notes, returns and genuine reductions.

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
