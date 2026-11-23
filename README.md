# SDCE Reports

Frappe / ERPNext app (`sdce_reports`) that holds every report SDCE develops or adds to its ERPNext system.
One place, version controlled, tested, installed with `bench`.

تطبيق Frappe / ERPNext يجمع كل التقارير التي تطوّرها أو تضيفها SDCE على نظام ERPNext، في مكان واحد مُدار بالإصدارات ومُختبر.

## Requirements

- Frappe v16, ERPNext v16
- Python 3.14

## Reports

| Report | Purpose |
|---|---|
| **KSA VAT Return** (إقرار ضريبة القيمة المضافة) | Saudi VAT return fields 1–16: amount, adjustment and VAT columns, laid out like the official return form. Every amount links to its transactions. Print view for A4. |
| **KSA VAT Return Detail** (تفاصيل إقرار ضريبة القيمة المضافة) | The vouchers behind each amount: voucher no, supplier / customer invoice no, party, tax ID, taxable amount, VAT, total including VAT, VAT account. Export to Excel or PDF from the report menu. |

### KSA VAT Return: setup

1. Open **KSA VAT Settings**, pick the company and list its VAT accounts:
   - **Output VAT**: VAT charged on sales.
   - **Input VAT**: VAT paid on purchases.
   - **VAT Settlement**: the account that receives the balance when a return is closed or paid, and any clearing
     account between VAT accounts.
2. Set **Tax Rate** on each Output / Input VAT account (used for journal entries, where the taxable amount is
   derived from the VAT).

### KSA VAT Return: how amounts are found

- **Sales and Purchase Invoices** (submitted): item level taxable amount and VAT from Item Wise Tax Detail for tax
  rows on an Output VAT (sales) or Input VAT (purchases) account. Credit notes, debit notes and purchase returns go
  to the **Adjustment** column. A zero-rated sale to a customer whose address country is not the company's country
  is an **Export**.
- **Other vouchers** (Journal Entry, Payment Entry, ...) posting to an Output or Input VAT account: VAT from the GL,
  taxable amount = VAT × 100 ÷ account Tax Rate.
- **Not reported**: opening entries, and vouchers whose GL entries only move amounts between the configured VAT
  accounts (closing a return into the settlement account, paying it, reclassifications). The detail report lists
  them when **Show Excluded Entries** is set, so every VAT ledger movement can be traced.

### Known limits

- Fields 2 (citizens' healthcare / education), 5 and 11 (exempt), 8 (imports at customs), 9 (reverse charge),
  14 (corrections) and 15 (credit carried forward) are not calculated yet and show zero or blank.
- Input VAT is reported as booked. The report does not decide whether it is recoverable; review the detail report
  (supplier invoice number and tax ID) before filing.
- This app is not affiliated with or certified by ZATCA. Check the figures against your books before filing.

## Install

```bash
bench get-app https://github.com/SDe-ER/reports
bench --site <site> install-app sdce_reports
```

## Development

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app sdce_reports
```

All changes go through a pull request. Do not commit company data, exports, backups or credentials.

## License

GPL-3.0-or-later
