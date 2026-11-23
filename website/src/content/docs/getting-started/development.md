---
title: Development
description: Running the tests, the checks every pull request passes, and adding a new report.
sidebar:
  order: 4
---

## Run the tests

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app sijill
```

Tests create their own synthetic company, accounts, parties and documents, and roll back after each test. Never run
them on a production site.

## Pull request checks

Every pull request runs **CI**: a fresh bench with Frappe and ERPNext `version-16`, the app installed on a new site,
and all tests. Before opening a pull request, also run:

```bash
ruff format sijill && ruff check sijill
```

## Adding a report

1. Create a standard report in the **Sijill** module: `sijill/sijill/report/<report_name>/`.
2. Read data with parameterised queries (`frappe.db.sql` with `%(name)s` values, or `frappe.qb`). Never build SQL
   from user input.
3. Check the company permission and validate the filters before running any query.
4. Put company-specific choices (accounts, rates) in a settings DocType, never in the code.
5. Write tests in `test_<report_name>.py` next to the report, including the totals of the summary against its detail.
6. Add the Arabic translation of every new label to `sijill/locale/ar.po`.
7. Add a page for the report under `website/src/content/docs/reports/` (English) and
   `website/src/content/docs/ar/reports/` (Arabic), and an entry in **What's new**.

## Rules

- Do not commit company data: names, tax IDs, invoices, exports, backups or credentials.
- Reports are read only. They never write documents or ledger entries.
