# Deployments

Public record of the Sijill versions deployed to the SDCE Production site. Versions, tags, commits and dates only;
the operational record (backups, images, checks) is kept in the private SDCE workspace.

| Version | Tag | Commit | Deployed (UTC) | Notes |
|---|---|---|---|---|
| 0.1.5 | [v0.1.5](https://github.com/SDe-ER/reports/releases/tag/v0.1.5) | `6c5d1ab` | 2026-11-24 08:00 | VAT return built from invoices from a cutoff date (KSA VAT Settings); purchase data rules; report VAT Documents Requiring Completion; Custom Field fixture. Upgrade from 0.1.4 (migrate). |
| 0.1.4 | [v0.1.4](https://github.com/SDe-ER/reports/releases/tag/v0.1.4) | `a0e8d02` | 2026-11-23 23:50 | Bank name from the Bank Account's Bank on entries without a party; field 14 label "between SAR ±15,000" (en + ar). Upgrade from 0.1.3 (migrate). |
| 0.1.3 | [v0.1.3](https://github.com/SDe-ER/reports/releases/tag/v0.1.3) | `1a7e827` | 2026-11-23 22:29 | Effective VAT rate for "Actual" VAT rows (fields 7/10 and 1/3), bank name on entries without a party, print greys. Upgrade from 0.1.2 (migrate). |
| 0.1.2 | [v0.1.2](https://github.com/SDe-ER/reports/releases/tag/v0.1.2) | `2dab957` | 2026-11-23 18:03 | Sijill workspace, sidebar, desktop icon and apps-screen entry; standard print layout of the VAT return. Upgrade from 0.1.1 (migrate). |
| 0.1.1 | [v0.1.1](https://github.com/SDe-ER/reports/releases/tag/v0.1.1) | `0ad7e9c` | 2026-11-23 13:11 | VAT charged by the bank on its fees reported in field 7. Upgrade from 0.1.0 (migrate). |
| 0.1.0 | [v0.1.0](https://github.com/SDe-ER/reports/releases/tag/v0.1.0) | `08856d9` | 2026-11-23 11:13 | First install (`install-app sijill`). |

Rollback of an upgrade returns to the previous version's code only; data entered after the deployment is kept.
