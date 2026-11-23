---
title: Introduction
description: What Sijill is, who it is for and how its reports work.
sidebar:
  order: 1
---

Sijill is a Frappe app that holds reports added to ERPNext. Instead of one-off query reports typed into a
site, every report lives in this repository as a **standard report**: its code is reviewed, tested on a clean site,
translated, and installed or upgraded with `bench`, like the reports that ship with ERPNext.

## Main ideas

- **Read only.** Reports read submitted documents and the general ledger. They never create, change or delete
  documents or ledger entries.
- **Settings, not code.** Anything specific to a company (accounts, rates) is chosen in a settings form on the site.
  The repository holds no company data.
- **Traceable.** A summary report and its detail report use the same calculation, so every total can be followed to
  the vouchers behind it.
- **Bilingual.** Labels are written in English and translated to Arabic in `sijill/locale/ar.po`.

## Reports

| Report | What it shows |
|---|---|
| [KSA VAT Return](/reports/reports/ksa-vat-return/) | The Saudi VAT return, fields 1 to 16. |
| [KSA VAT Return Detail](/reports/reports/ksa-vat-return-detail/) | The vouchers behind each amount of the return. |

:::caution
Sijill is not affiliated with or certified by ZATCA. Check every figure against your books before you file a
return.
:::
