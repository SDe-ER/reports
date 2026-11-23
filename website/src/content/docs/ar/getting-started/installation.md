---
title: التثبيت
description: المتطلبات وتثبيت تقارير SDCE بأداة bench.
sidebar:
  order: 2
---

## المتطلبات

| المكوّن | الإصدار |
|---|---|
| Frappe Framework | v16 |
| ERPNext | v16 (تطبيق مطلوب) |
| Python | 3.14 |

## التثبيت بأداة bench

نفّذ الأوامر من مجلد bench، واستبدل `<your-site>` باسم موقعك.

```bash
cd frappe-bench
bench get-app https://github.com/SDe-ER/reports --branch main
bench --site <your-site> install-app sdce_reports
```

يضيف التثبيت التقارير ونموذج **إعدادات ضريبة القيمة المضافة السعودية**، ولا يغيّر أي مستند أو إعداد موجود.

## التحديث

```bash
bench update --apps sdce_reports
```

أو يدوياً:

```bash
cd apps/sdce_reports && git pull && cd ../..
bench --site <your-site> migrate
```

## إزالة التطبيق

```bash
bench --site <your-site> uninstall-app sdce_reports
```

الإزالة تحذف التقارير ونموذج الإعدادات فقط. المستندات والقيود لا تُمس.
