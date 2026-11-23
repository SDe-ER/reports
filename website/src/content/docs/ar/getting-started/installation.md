---
title: التثبيت
description: المتطلبات وتثبيت سِجِلّ (Sijill) بأداة bench.
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
bench --site <your-site> install-app sijill
```

يضيف التثبيت التقارير ونموذج **إعدادات ضريبة القيمة المضافة السعودية** وصفحة **سِجِلّ** (قائمة جانبية، وأيقونة في شاشة التطبيقات وسطح المكتب)، ولا يغيّر أي مستند أو إعداد موجود.

## التحديث

```bash
bench update --apps sijill
```

أو يدوياً:

```bash
cd apps/sijill && git pull && cd ../..
bench --site <your-site> migrate
```

## إزالة التطبيق

```bash
bench --site <your-site> uninstall-app sijill
```

الإزالة تحذف التقارير ونموذج الإعدادات فقط. المستندات والقيود لا تُمس.
