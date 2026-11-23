# Contributing to Sijill

Thanks for your interest in improving Sijill. Sijill is a standalone app built on the Frappe Framework and ERPNext.

## Ground rules

- **No real data.** Never put real company, customer, supplier or financial data in code, tests, fixtures,
  screenshots or issues. Use invented data only.
- **Reports are read only.** A report never creates, changes or deletes documents or ledger entries.
- **Server-side logic.** Calculations and validation live in the report and DocType Python code, not in client scripts.
- **Settings, not code.** Anything specific to a company (accounts, rates) is chosen in a settings DocType.
- **Standard-first.** Prefer standard Frappe / ERPNext mechanisms; never edit Frappe or ERPNext core.

## Development setup

You need a working [bench](https://frappeframework.com/docs) with **Frappe v16** and **ERPNext v16**.

```bash
# in your bench
bench get-app /path/to/reports        # or your fork's URL
bench --site <dev-site> install-app sijill
```

## Tests

```bash
bench --site <dev-site> set-config allow_tests true
bench --site <dev-site> run-tests --app sijill
```

Add or update tests for any behaviour change. A summary report must have a test that reconciles its totals with
its detail report.

## Linting

```bash
ruff format sijill && ruff check sijill
```

## Pull requests

1. Branch off `main` with a descriptive name.
2. Keep each pull request focused.
3. PR titles follow [Conventional Commits](https://www.conventionalcommits.org/), e.g. `feat(reports): …`,
   `fix: …`, `docs: …`.
4. Update `CHANGELOG.md` under **Unreleased**, and the docs site: "What's new" in English and Arabic
   (`website/src/content/docs/releases/whats-new.md`, `website/src/content/docs/ar/releases/whats-new.md`) and the
   page of every report you add or change.
5. Add every new report to the **Sijill** page (sidebar and workspace). A test checks the sidebar.
6. Add the Arabic translation of every new label to `sijill/locale/ar.po`.
7. Ensure CI is green (tests on Frappe and ERPNext version-16, CodeQL, docs build).
8. A maintainer review is required (see `.github/CODEOWNERS`).

The [development guide](https://sde-er.github.io/reports/getting-started/development/) explains how to add a report.

## Reporting bugs and requesting features

Use the issue templates. For **security vulnerabilities**, do not open a public issue: email **info@sdce.sa**
(see [SECURITY.md](SECURITY.md)).
