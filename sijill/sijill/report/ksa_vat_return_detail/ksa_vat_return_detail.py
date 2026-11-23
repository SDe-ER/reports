# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""KSA VAT Return Detail: the vouchers behind every amount of the KSA VAT Return."""

import frappe
from frappe import _
from frappe.utils import flt

from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	PURCHASE_CATEGORIES,
	SALES_CATEGORIES,
	get_vat_lines,
	validate_filters,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	lines = get_vat_lines(filters, include_excluded=bool(filters.get("show_excluded")))
	lines = [line for line in lines if matches(line, filters)]
	add_tax_ids(lines)

	currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	data = []
	for line in lines:
		line.currency = currency
		line.grand_total = flt(flt(line.taxable_amount) + flt(line.vat_amount), 2)
		data.append(line)
	return get_columns(), data


def matches(line, filters):
	side = filters.get("side")
	if side == "Sales" and line.category not in SALES_CATEGORIES:
		return False
	if side == "Purchase" and line.category not in PURCHASE_CATEGORIES:
		return False
	if filters.get("category") and line.category != filters.category:
		return False
	if filters.get("rate") not in (None, "") and flt(line.rate) != flt(filters.rate):
		return False
	if filters.get("party_type") and line.party_type != filters.party_type:
		return False
	if filters.get("party") and line.party != filters.party:
		return False
	if filters.get("voucher_type") and line.voucher_type != filters.voucher_type:
		return False
	return True


def add_tax_ids(lines):
	for party_type in ("Customer", "Supplier"):
		parties = {line.party for line in lines if line.party_type == party_type and line.party}
		if not parties:
			continue
		tax_ids = dict(
			frappe.get_all(
				party_type, filters={"name": ("in", list(parties))}, fields=["name", "tax_id"], as_list=True
			)
		)
		for line in lines:
			if line.party_type == party_type:
				line.tax_id = tax_ids.get(line.party)


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
		{
			"fieldname": "bill_no",
			"label": _("Invoice No", context="KSA VAT Return"),
			"fieldtype": "Data",
			"width": 140,
		},
		{"fieldname": "bill_date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 100},
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
		{"fieldname": "tax_id", "label": _("Tax ID"), "fieldtype": "Data", "width": 140},
		{"fieldname": "category", "label": _("VAT Category"), "fieldtype": "Data", "width": 170},
		{"fieldname": "rate", "label": _("Rate (%)"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "is_adjustment", "label": _("Adjustment"), "fieldtype": "Check", "width": 90},
		{
			"fieldname": "taxable_amount",
			"label": _("Taxable Amount", context="KSA VAT Return"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "grand_total",
			"label": _("Total Including VAT"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{"fieldname": "vat_account", "label": _("VAT Account"), "fieldtype": "Data", "width": 180},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 220},
	]
