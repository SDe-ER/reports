# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""VAT Documents Requiring Completion: the vouchers the KSA VAT Return leaves out or warns about.

One row per voucher and side. Rules and their texts: ksa_vat_return/data_rules.py.
"""

import frappe
from frappe import _

from sijill.sijill.report.ksa_vat_return.data_rules import STATUS_NOT_REPORTED, get_rule_result
from sijill.sijill.report.ksa_vat_return.ksa_vat_return import validate_filters


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	_included, rows = get_rule_result(filters)

	if filters.get("side"):
		rows = [row for row in rows if row.side == filters.side]
	if not filters.get("show_not_reported"):
		rows = [row for row in rows if row.status != STATUS_NOT_REPORTED]

	currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	for row in rows:
		row.currency = currency
		row.open = row.voucher_no
	return get_columns(), rows


def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date", context="KSA VAT Return"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type", context="KSA VAT Return"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher No", context="KSA VAT Return"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 170,
		},
		{"fieldname": "party_type", "label": _("Party Type"), "fieldtype": "Data", "width": 90, "hidden": 1},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150,
		},
		{
			"fieldname": "party_name",
			"label": _("Party Name", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "bill_no",
			"label": _("Invoice No", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 140,
		},
		{"fieldname": "tax_id", "label": _("Tax ID"), "fieldtype": "Data", "width": 140},
		{
			"fieldname": "taxable_amount",
			"label": _("Taxable Amount", context="KSA VAT Return"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount", context="KSA VAT Return"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "reclass_pair",
			"label": _("Reclassification Pair", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 170,
		},
		{"fieldname": "side", "label": _("Sales / Purchase"), "fieldtype": "Data", "width": 90},
		{
			"fieldname": "status",
			"label": _("Status", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "failed_codes",
			"label": _("Rule Codes", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "failed_rules_en",
			"label": _("Failed Rules (English)", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 320,
		},
		{
			"fieldname": "failed_rules_ar",
			"label": _("Failed Rules (Arabic)", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 320,
		},
		{"fieldname": "open", "label": _("Open", context="KSA VAT Return"), "fieldtype": "Data", "width": 80},
	]
