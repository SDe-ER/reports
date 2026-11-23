# SDCE Reports

Frappe / ERPNext app (`sdce_reports`) that holds every report SDCE develops or adds to its ERPNext system.
One place, version controlled, tested, installed with `bench`.

تطبيق Frappe / ERPNext يجمع كل التقارير التي تطوّرها أو تضيفها SDCE على نظام ERPNext، في مكان واحد مُدار بالإصدارات ومُختبر.

## Requirements

- Frappe v16, ERPNext v16
- Python 3.14

## Reports

See the pull requests: each report is added with its own tests.

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
