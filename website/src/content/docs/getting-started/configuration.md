---
title: Configuration
description: The settings each report needs before it runs.
sidebar:
  order: 3
---

## KSA VAT Settings

The VAT reports need to know which accounts hold VAT. Open **KSA VAT Settings**, create a record for each company in
Saudi Arabia and list its accounts:

| Type | Use it for |
|---|---|
| **Output VAT** | VAT charged on sales. |
| **Input VAT** | VAT paid on purchases. |
| **VAT Settlement** | The account that receives the VAT balance when a return is closed or paid, and any clearing account used to move amounts between VAT accounts. |

Rules checked when you save:

- The company must be in Saudi Arabia.
- Each account belongs to the company, is not a group, and is listed once.
- At least one Output VAT and one Input VAT account.

## Tax rate on VAT accounts

Set **Tax Rate** on each Output VAT and Input VAT account (Chart of Accounts, open the account). Journal entries do
not carry a taxable amount, so the reports derive it from the VAT: taxable amount = VAT × 100 ÷ tax rate. An account
without a tax rate reports its VAT with a taxable amount of zero.

## Permissions

| Role | Access |
|---|---|
| Accounts Manager, System Manager | Edit KSA VAT Settings |
| Accounts User | Read KSA VAT Settings |
| Accounts User, Accounts Manager, Auditor | Run the VAT reports |

A user only sees companies they are allowed to see.
