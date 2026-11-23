---
title: Installation
description: Requirements and installing SDCE Reports with bench.
sidebar:
  order: 2
---

## Requirements

| Component | Version |
|---|---|
| Frappe Framework | v16 |
| ERPNext | v16 (required app) |
| Python | 3.14 |

## Install with bench

Run these commands from your bench directory. Replace `<your-site>` with your site name.

```bash
cd frappe-bench
bench get-app https://github.com/SDe-ER/reports --branch main
bench --site <your-site> install-app sdce_reports
```

The installer adds the reports and the **KSA VAT Settings** form. It does not change existing documents
or settings.

## Upgrade

```bash
bench update --apps sdce_reports
```

or, on a bench you manage by hand:

```bash
cd apps/sdce_reports && git pull && cd ../..
bench --site <your-site> migrate
```

## Uninstall

```bash
bench --site <your-site> uninstall-app sdce_reports
```

Uninstalling removes the reports and the settings form. Your documents and ledger entries are not touched.
