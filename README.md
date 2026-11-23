<div align="center">

<img src="sijill/public/images/sijill-logo-512.png" alt="Sijill logo" height="96">

<h1>Sijill</h1>

**Reports for Frappe and ERPNext, starting with the Saudi VAT return**

<p dir="rtl">سِجِلّ: تقارير Frappe و ERPNext، بدءاً بإقرار ضريبة القيمة المضافة السعودي</p>

[![CI](https://github.com/SDe-ER/reports/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SDe-ER/reports/actions/workflows/ci.yml)
[![CodeQL](https://github.com/SDe-ER/reports/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/SDe-ER/reports/actions/workflows/codeql.yml)
[![Docs site](https://github.com/SDe-ER/reports/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/SDe-ER/reports/actions/workflows/docs.yml)
[![Latest release](https://img.shields.io/github/v/release/SDe-ER/reports?label=release)](https://github.com/SDe-ER/reports/releases/latest)
[![License: GPL-3.0](https://img.shields.io/github/license/SDe-ER/reports)](LICENSE)
[![Frappe and ERPNext v16](https://img.shields.io/badge/Frappe%20%7C%20ERPNext-v16-0089FF)](https://github.com/frappe/erpnext)

<br>

[![Documentation](https://img.shields.io/badge/Documentation-English-0089FF?style=for-the-badge&logo=readthedocs&logoColor=white)](https://sde-er.github.io/reports/)
[![التوثيق بالعربية](https://img.shields.io/badge/Documentation-Arabic-0A7B4F?style=for-the-badge&logo=readthedocs&logoColor=white)](https://sde-er.github.io/reports/ar/)

[What's new](https://sde-er.github.io/reports/releases/whats-new/) ·
[Installation](https://sde-er.github.io/reports/getting-started/installation/) ·
[Reports](https://sde-er.github.io/reports/reports/ksa-vat-return/) ·
[Releases](https://github.com/SDe-ER/reports/releases)

</div>

<br>

Sijill (سِجِلّ, "record") is a Frappe application for the reports you add to ERPNext. Each report is a standard
report: built from your submitted documents and general ledger, read only, tested on a clean site, translated to
Arabic and installed with bench. Nothing specific to a company is in the code: accounts and rates are chosen in
settings on your site.

## Highlights

- **KSA VAT Return**: the Saudi VAT return, fields 1 to 16, with amount, adjustment and VAT columns, laid out like
  the official form, with an A4 print view.
- **Every amount traceable**: click any amount to open **KSA VAT Return Detail**, the vouchers behind it with
  supplier / customer invoice numbers, parties, tax IDs, taxable amount, VAT and total including VAT.
- **Settlements kept apart**: closing, paying and reclassifying VAT, and opening entries, are not reported as
  transactions, and stay visible in the detail report.
- **Excel and PDF** export from the standard report menu.
- **Arabic and English** for every label, report and print.

## Quick start

```bash
bench get-app https://github.com/SDe-ER/reports --branch main
bench --site <your-site> install-app sijill
```

Requires Frappe and ERPNext v16. Then open **KSA VAT Settings** and pick the company's VAT accounts. See the
[installation guide](https://sde-er.github.io/reports/getting-started/installation/) and
[configuration](https://sde-er.github.io/reports/getting-started/configuration/).

## Documentation

Everything else lives on the documentation site, in English and Arabic:

| | |
|---|---|
| [Getting started](https://sde-er.github.io/reports/getting-started/introduction/) | Introduction, installation, configuration, development |
| [Reports](https://sde-er.github.io/reports/reports/ksa-vat-return/) | Every report with its fields, filters and columns |
| [What's new](https://sde-er.github.io/reports/releases/whats-new/) | Every change and release in plain language |

> Sijill is not affiliated with or certified by ZATCA. Check every figure against your books before you file a return.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the
[development guide](https://sde-er.github.io/reports/getting-started/development/), and follow the
[code of conduct](CODE_OF_CONDUCT.md). Changes are recorded in the [CHANGELOG](CHANGELOG.md).
Security issues: see [SECURITY.md](SECURITY.md).

## License

[GPL-3.0-or-later](LICENSE)
