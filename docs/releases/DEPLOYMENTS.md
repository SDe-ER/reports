# Deployments

Public record of the Sijill versions deployed to the SDCE Production site. Versions, tags, commits and dates only;
the operational record (backups, images, checks) is kept in the private SDCE workspace.

| Version | Tag | Commit | Deployed (UTC) | Notes |
|---|---|---|---|---|
| 0.1.2 | [v0.1.2](https://github.com/SDe-ER/reports/releases/tag/v0.1.2) | `2dab957` | 2026-11-23 18:03 | Sijill workspace, sidebar, desktop icon and apps-screen entry; standard print layout of the VAT return. Upgrade from 0.1.1 (migrate). |
| 0.1.1 | [v0.1.1](https://github.com/SDe-ER/reports/releases/tag/v0.1.1) | `0ad7e9c` | 2026-11-23 13:11 | VAT charged by the bank on its fees reported in field 7. Upgrade from 0.1.0 (migrate). |
| 0.1.0 | [v0.1.0](https://github.com/SDe-ER/reports/releases/tag/v0.1.0) | `08856d9` | 2026-11-23 11:13 | First install (`install-app sijill`). |

Rollback of an upgrade returns to the previous version's code only; data entered after the deployment is kept.
