---
title: KSA VAT Return Detail
description: The vouchers behind every amount of the KSA VAT Return, with Excel and PDF export.
sidebar:
  order: 2
---

**KSA VAT Return Detail** lists the vouchers behind each amount of the [KSA VAT Return](/reports/reports/ksa-vat-return/).
It uses the same calculation as the return, so its totals always match.

## Filters

| Filter | Notes |
|---|---|
| Company, From Date, To Date | Required. Filled for you when you open the report from an amount of the return. |
| Sales / Purchase | Sales or purchases only. |
| VAT Category | Standard Rated Sales, Zero Rated Domestic Sales, Exports, Standard Rated Purchases, Zero Rated Purchases. |
| Rate (%) | For example 15. |
| Party Type, Party | One customer or supplier. |
| Voucher Type | Sales Invoice, Purchase Invoice, Journal Entry, Payment Entry. |
| Show Excluded Entries | Adds opening entries and entries between VAT accounts, greyed, with the reason in Remarks. |

## Columns

| Column | Content |
|---|---|
| Posting Date | Date of the voucher. |
| Voucher Type, Voucher No | The ERPNext document, with a link to open it. |
| Invoice No, Invoice Date | Purchases: the supplier's invoice number and date. Sales: the sales invoice. Journal entries: the bill or reference number. |
| Party, Party Name | Customer or supplier. |
| Tax ID | The party's VAT registration number. |
| VAT Category, Rate (%) | Where the line goes in the return. |
| Adjustment | Ticked for credit notes, debit notes and returns. |
| Taxable Amount, VAT Amount, Total Including VAT | In company currency. |
| VAT Account | The VAT account the amount was posted to. |
| Remarks | Why an excluded line is not reported. |

The last row totals the amount columns.

## Export

Use the report menu: **Export** for Excel or CSV, **Print** or **PDF** for a PDF. The export contains the filtered rows
and the total.

## Checking a return

1. Open the return for the quarter.
2. Click the VAT amount of field 7 (purchases).
3. Sort by **Invoice No** and **Tax ID**: lines without a supplier invoice number or tax ID need review before their
   input VAT is claimed.
4. Tick **Show Excluded Entries** to see the settlement and reclassification entries of the period.
