# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""Data rules of the KSA VAT Return.

Every voucher behind the return is checked for the data a VAT return needs.

Purchase side (input VAT): a voucher that fails any rule is left out of the return and of the detail report
and is listed in "VAT Documents Requiring Completion" with the status "Excluded". Input VAT is deducted only
with a valid tax invoice in hand (ZATCA Guideline for Tax Invoicing and Records under VAT Provisions v3, May
2026, sections 9.1 and 9.4); a document received later can be deducted in a later period (Implementing
Regulations Article 49).

Sales side (output VAT): never left out, because VAT is collected on every taxable sale (same guideline,
section 1.3). Missing customer data is only reported, with the status "Included (warning)". A simplified tax
invoice carries no customer details (section 4.3, Implementing Regulations Article 53).

Settlement and opening entries are not part of the rules; they are listed with the status "Not reported".

All lookups are batched: one query per document type and rule, never one per line.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt

from sijill.sijill.doctype.ksa_vat_settings.ksa_vat_settings import get_ksa_vat_accounts
from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	EXCLUDED,
	PURCHASE_CATEGORIES,
	SALES_CATEGORIES,
	get_vat_lines,
)

# rule code -> (English text, Arabic text); both languages are always shown by the exceptions report
RULES = {
	"BILL_NO_MISSING": ("Supplier invoice number is missing", "رقم فاتورة المورد غير موجود"),
	"BILL_NO_DUPLICATE": (
		"Supplier invoice number is used on more than one voucher of the same supplier",
		"رقم فاتورة المورد مكرر على أكثر من مستند للمورد نفسه",
	),
	"SUPPLIER_NAME_MISSING": ("Supplier name is missing", "اسم المورد غير موجود"),
	"SUPPLIER_VAT_INVALID": (
		"Supplier VAT number is missing or invalid (15 digits, starts and ends with 3)",
		"الرقم الضريبي للمورد غير موجود أو غير صحيح (15 رقماً يبدأ وينتهي بالرقم 3)",
	),
	"BUYER_DETAILS_NOT_VERIFIED": (
		"Company details on the supplier invoice are not verified",
		"لم يتم التحقق من بيانات المؤسسة على فاتورة المورد",
	),
	"ATTACHMENT_MISSING": (
		"No attachment (copy of the supplier invoice)",
		"لا يوجد مرفق (صورة فاتورة المورد)",
	),
	"REDUCTION_EXCLUDED": (
		"Reduces input VAT: excluding it increases the VAT claim. Review it.",
		"هذا المستند يخفض ضريبة المدخلات: استبعاده يزيد المطالبة بالضريبة. راجعه.",
	),
	"CUSTOMER_NAME_MISSING": ("Customer name is missing", "اسم العميل غير موجود"),
	"CUSTOMER_ID_MISSING": (
		"Customer has no valid VAT number and no other ID",
		"العميل ليس له رقم ضريبي صحيح ولا رقم تعريف آخر",
	),
	"CUSTOMER_VAT_INVALID": (
		"Customer VAT number is invalid (15 digits, starts and ends with 3)",
		"الرقم الضريبي للعميل غير صحيح (15 رقماً يبدأ وينتهي بالرقم 3)",
	),
	"VAT_RECLASSIFIED": ("VAT reclassified (owner decision)", "ضريبة أعيد تصنيفها (قرار المالك)"),
	"RECLASS_PARTIAL": (
		"Partial VAT reclassification: not excluded. Review it.",
		"إعادة تصنيف جزئية للضريبة: لم تُستبعد. راجعها.",
	),
	"NOT_A_TAXABLE_TRANSACTION": (
		"Not a taxable transaction: settlement, VAT payment or opening entry",
		"ليست عملية خاضعة للضريبة: تسوية أو سداد ضريبة أو قيد افتتاحي",
	),
}

PURCHASE_RULES = (
	"BILL_NO_MISSING",
	"BILL_NO_DUPLICATE",
	"SUPPLIER_NAME_MISSING",
	"SUPPLIER_VAT_INVALID",
	"BUYER_DETAILS_NOT_VERIFIED",
	"ATTACHMENT_MISSING",
)

# 15 digits, starts and ends with 3
VAT_NUMBER_PATTERN = re.compile(r"^3[0-9]{13}3$")

BUYER_FIELD = "sijill_buyer_details_verified"
ADDITIONAL_IDS_FIELD = "custom_additional_ids"

STATUS_EXCLUDED = "Excluded"
STATUS_WARNING = "Included (warning)"
STATUS_NOT_REPORTED = "Not reported"
STATUS_RECLASSIFIED = "Reclassified"

RECLASS_FIELD = "sijill_reclassification_of"

# the supplier invoice number field of each voucher type
BILL_FIELDS = {"Purchase Invoice": "bill_no", "Journal Entry": "bill_no", "Payment Entry": "reference_no"}


def get_rule_result(filters):
	"""(included_lines, exception_rows) of the KSA VAT Return lines for the filters (company, from_date,
	to_date)."""
	filters = frappe._dict(filters)
	return evaluate_lines(get_vat_lines(filters, include_excluded=True), filters.company)


def evaluate_lines(lines, company):
	"""Apply the rules to lines from get_vat_lines(include_excluded=True).

	Returns (included_lines, exception_rows). included_lines are the lines of the return; their bill_no,
	party_name and tax_id are filled (a marker on sales lines where the data is missing). exception_rows has
	one row per voucher and side that is excluded, warned about or not reported.
	"""
	accounts = get_ksa_vat_accounts(company)
	lines, pair_rows, flags = exclude_reclass_pairs(lines, company)
	groups = {}
	for line in lines:
		not_reported = line.category == EXCLUDED
		side = get_side(line, accounts)
		groups.setdefault((line.voucher_type, line.voucher_no, side, not_reported), []).append(line)

	purchase_keys = [k for k, v in groups.items() if v[0].category in PURCHASE_CATEGORIES]
	sales_keys = [k for k, v in groups.items() if v[0].category in SALES_CATEGORIES]
	purchases = PurchaseFacts(company, accounts, purchase_keys, groups)
	sales = SalesFacts(sales_keys, groups)

	included = []
	exceptions = list(pair_rows)
	for key, group in groups.items():
		first = group[0]
		if first.category == EXCLUDED:
			exceptions.append(
				get_exception_row(group, key[2], STATUS_NOT_REPORTED, ["NOT_A_TAXABLE_TRANSACTION"])
			)
		elif first.category in PURCHASE_CATEGORIES:
			codes, details = purchases.check(key, group)
			extra = get_flags(flags, key)
			if not codes:
				for line in group:
					line.update(details)
				included += group
				if extra:
					exceptions.append(get_exception_row(group, key[2], STATUS_WARNING, extra))
				continue
			codes += extra
			vat = sum(flt(line.vat_amount) for line in group)
			if vat < 0:
				codes.append("REDUCTION_EXCLUDED")
			row = get_exception_row(group, key[2], STATUS_EXCLUDED, codes)
			row.update({k: v for k, v in details.items() if v})
			exceptions.append(row)
		else:
			codes, details = sales.check(key, group)
			codes += get_flags(flags, key)
			for line in group:
				line.update(details)
			included += group
			if codes:
				row = get_exception_row(group, key[2], STATUS_WARNING, codes)
				row.tax_id = None if details["tax_id"] == get_marker() else details["tax_id"]
				exceptions.append(row)

	included.sort(key=lambda d: (str(d.posting_date), d.voucher_type, d.voucher_no))
	exceptions.sort(key=lambda d: (str(d.posting_date), d.voucher_type, d.voucher_no))
	return included, exceptions


def get_flags(flags, key):
	return list(flags.get(key[1], [])) if key[0] == "Journal Entry" else []


def get_side(line, accounts):
	if line.category in SALES_CATEGORIES:
		return "Sales"
	if line.category in PURCHASE_CATEGORIES:
		return "Purchase"
	account_type = accounts.get(line.vat_account)
	return {"Output VAT": "Sales", "Input VAT": "Purchase"}.get(account_type, "")


def get_exception_row(group, side, status, codes):
	first = group[0]
	row = frappe._dict(
		posting_date=first.posting_date,
		voucher_type=first.voucher_type,
		voucher_no=first.voucher_no,
		party_type=first.party_type,
		party=first.party,
		party_name=first.party_name,
		bill_no=first.bill_no,
		tax_id=None,
		taxable_amount=flt(sum(flt(line.taxable_amount) for line in group), 2),
		vat_amount=flt(sum(flt(line.vat_amount) for line in group), 2),
		side=side,
		status=status,
		failed_codes="; ".join(codes),
		failed_rules_en="; ".join(RULES[code][0] for code in codes),
		failed_rules_ar="; ".join(RULES[code][1] for code in codes),
		reclass_pair=None,
	)
	return row


def get_marker():
	return _("Missing - see VAT Documents Requiring Completion")


def is_valid_vat_number(value):
	return bool(VAT_NUMBER_PATTERN.match((value or "").strip()))


def get_records(doctype, names, fields):
	"""name -> record for the given names, in one query. Permissions are not applied: the rules need the facts."""
	if not names:
		return {}
	rows = frappe.get_all(doctype, filters={"name": ("in", sorted(names))}, fields=["name", *fields])
	return {row.name: row for row in rows}


class PurchaseFacts:
	"""Facts of the purchase vouchers, loaded in a few batched queries."""

	def __init__(self, company, accounts, keys, groups):
		self.docs = {}
		for voucher_type in {k[0] for k in keys}:
			names = {k[1] for k in keys if k[0] == voucher_type}
			self.docs[voucher_type] = self.load_vouchers(voucher_type, names)

		suppliers = {
			groups[key][0].party
			for key in keys
			if groups[key][0].party_type == "Supplier" and groups[key][0].party
		}
		self.suppliers = get_records("Supplier", suppliers, ["supplier_name", "tax_id"])
		self.bill_keys = self.load_bill_keys(company, accounts, suppliers)
		self.attached = {
			voucher_type: self.load_attached(voucher_type, names) for voucher_type, names in self.names(keys)
		}

	@staticmethod
	def names(keys):
		by_type = {}
		for key in keys:
			by_type.setdefault(key[0], set()).add(key[1])
		return by_type.items()

	@staticmethod
	def load_vouchers(voucher_type, names):
		fields = []
		if voucher_type == "Purchase Invoice":
			fields += ["supplier", "supplier_name", "is_return"]
		if voucher_type in BILL_FIELDS:
			fields.append(BILL_FIELDS[voucher_type])
		if frappe.get_meta(voucher_type).has_field(BUYER_FIELD):
			fields.append(BUYER_FIELD)
		return get_records(voucher_type, names, fields)

	@staticmethod
	def load_attached(voucher_type, names):
		return set(
			frappe.get_all(
				"File",
				filters={"attached_to_doctype": voucher_type, "attached_to_name": ("in", sorted(names))},
				pluck="attached_to_name",
			)
		)

	@staticmethod
	def load_bill_keys(company, accounts, suppliers):
		"""(supplier, bill no) -> the submitted vouchers of the company that carry it, over all dates."""
		keys = {}
		if not suppliers:
			return keys
		invoices = frappe.get_all(
			"Purchase Invoice",
			filters={
				"company": company,
				"docstatus": 1,
				"is_return": 0,
				"supplier": ("in", sorted(suppliers)),
				"bill_no": ("is", "set"),
			},
			fields=["name", "supplier", "bill_no"],
		)
		for row in invoices:
			add_bill_key(keys, row.supplier, row.bill_no, "Purchase Invoice", row.name)

		input_accounts = [a for a, t in accounts.items() if t == "Input VAT"]
		if input_accounts:
			entries = frappe.db.sql(
				"""
				select distinct je.name, jea.party, je.bill_no
				from `tabJournal Entry` je
				inner join `tabJournal Entry Account` jea on jea.parent = je.name
				where je.docstatus = 1
					and je.company = %(company)s
					and ifnull(je.bill_no, '') != ''
					and jea.party_type = 'Supplier'
					and jea.party in %(suppliers)s
					and exists(
						select 1 from `tabJournal Entry Account` v
						where v.parent = je.name and v.account in %(input_accounts)s
					)
				""",
				{"company": company, "suppliers": sorted(suppliers), "input_accounts": input_accounts},
				as_dict=True,
			)
			for row in entries:
				add_bill_key(keys, row.party, row.bill_no, "Journal Entry", row.name)
		return keys

	def check(self, key, group):
		"""(failed rule codes, details to put on the lines) of one purchase voucher."""
		voucher_type, voucher_no = key[0], key[1]
		first = group[0]
		doc = self.docs.get(voucher_type, {}).get(voucher_no) or {}
		supplier = first.party if first.party_type == "Supplier" and first.party else None
		master = self.suppliers.get(supplier) or {}

		bill_field = BILL_FIELDS.get(voucher_type)
		bill_no = (doc.get(bill_field) or "").strip() if bill_field else ""
		if voucher_type == "Purchase Invoice":
			supplier_name = (doc.get("supplier_name") or "").strip()
		else:
			supplier_name = (master.get("supplier_name") or "").strip()
		tax_id = (master.get("tax_id") or "").strip()

		failed = set()
		if not bill_no:
			failed.add("BILL_NO_MISSING")
		elif supplier and not (voucher_type == "Purchase Invoice" and doc.get("is_return")):
			holders = self.bill_keys.get((supplier, bill_no.casefold()), set()) | {(voucher_type, voucher_no)}
			if len(holders) > 1:
				failed.add("BILL_NO_DUPLICATE")
		if not supplier_name:
			failed.add("SUPPLIER_NAME_MISSING")
		if not is_valid_vat_number(tax_id):
			failed.add("SUPPLIER_VAT_INVALID")
		if not doc.get(BUYER_FIELD):
			failed.add("BUYER_DETAILS_NOT_VERIFIED")
		if voucher_no not in self.attached.get(voucher_type, set()):
			failed.add("ATTACHMENT_MISSING")

		codes = [code for code in PURCHASE_RULES if code in failed]
		return codes, {"bill_no": bill_no, "party_name": supplier_name, "tax_id": tax_id}


def add_bill_key(keys, supplier, bill_no, voucher_type, voucher_no):
	keys.setdefault((supplier, bill_no.strip().casefold()), set()).add((voucher_type, voucher_no))


class SalesFacts:
	"""Customer facts of the sales vouchers, loaded in a few batched queries."""

	def __init__(self, keys, groups):
		customers = {
			groups[key][0].party
			for key in keys
			if groups[key][0].party_type == "Customer" and groups[key][0].party
		}
		self.customers = get_records("Customer", customers, ["customer_name", "tax_id"])
		self.other_ids = self.load_other_ids(customers)

	@staticmethod
	def load_other_ids(customers):
		"""customer -> first additional ID with a value, as "<type>: <value>". The optional table field is
		read only when the Customer DocType has it."""
		if not customers or not frappe.get_meta("Customer").has_field(ADDITIONAL_IDS_FIELD):
			return {}
		child_doctype = frappe.get_meta("Customer").get_field(ADDITIONAL_IDS_FIELD).options
		child_meta = frappe.get_meta(child_doctype)
		if not child_meta.has_field("value"):
			return {}
		fields = ["parent", "value", *[f for f in ("type_name", "type_code") if child_meta.has_field(f)]]
		rows = frappe.get_all(
			child_doctype,
			filters={
				"parent": ("in", sorted(customers)),
				"parenttype": "Customer",
				"parentfield": ADDITIONAL_IDS_FIELD,
			},
			fields=fields,
			order_by="idx asc",
		)
		ids = {}
		for row in rows:
			value = (row.get("value") or "").strip()
			if value and row.parent not in ids:
				label = (row.get("type_name") or row.get("type_code") or "").strip()
				ids[row.parent] = f"{label}: {value}" if label else value
		return ids

	def check(self, key, group):
		"""(warning rule codes, details to put on the lines) of one sales voucher."""
		first = group[0]
		customer = first.party if first.party_type == "Customer" and first.party else None
		master = self.customers.get(customer) or {}
		name = (master.get("customer_name") or first.party_name or "").strip() if customer else ""
		tax_id = (master.get("tax_id") or "").strip()
		other_id = self.other_ids.get(customer)

		codes = []
		if not name:
			codes.append("CUSTOMER_NAME_MISSING")
		if not is_valid_vat_number(tax_id) and not other_id:
			codes.append("CUSTOMER_ID_MISSING")
		if tax_id and not is_valid_vat_number(tax_id):
			codes.append("CUSTOMER_VAT_INVALID")

		marker = get_marker()
		details = {
			"bill_no": (first.bill_no or "").strip() or first.voucher_no,
			"party_name": name or marker,
			"tax_id": tax_id or other_id or marker,
		}
		return codes, details


def exclude_reclass_pairs(lines, company):
	"""Take fully reclassified VAT out of the lines. Returns (remaining_lines, pair_rows, flags).

	A reclassification Journal Entry names the Journal Entry whose VAT it reverses in the custom field
	sijill_reclassification_of. For each (original, VAT account) the VAT of the original and the VAT of all its
	reclassification entries are summed over all dates, with the sign convention of get_gl_lines. When they cancel
	exactly, the original line and the reclassification lines on that account leave the lines (any period, both
	sides) and become pair_rows with the status "Reclassified" and the partner vouchers in `reclass_pair`.
	Otherwise nothing is removed; flags is {voucher_no: ["RECLASS_PARTIAL"]} for the vouchers involved, to merge
	with the data rule codes. Other lines are untouched. Works on get_vat_lines output.
	"""
	if not lines or not frappe.get_meta("Journal Entry").has_field(RECLASS_FIELD):
		return lines, [], {}
	accounts = get_ksa_vat_accounts(company)
	line_entries = {line.voucher_no for line in lines if line.voucher_type == "Journal Entry"}
	if not line_entries:
		return lines, [], {}

	# originals: the targets of the reclassification entries in the lines, and the entries in the lines
	# that may themselves be originals
	linked = frappe.get_all(
		"Journal Entry",
		filters={"name": ("in", sorted(line_entries)), RECLASS_FIELD: ("is", "set")},
		fields=["name", RECLASS_FIELD],
	)
	candidates = line_entries | {row[RECLASS_FIELD] for row in linked}
	reclass_rows = frappe.get_all(
		"Journal Entry",
		filters={"company": company, "docstatus": 1, RECLASS_FIELD: ("in", sorted(candidates))},
		fields=["name", RECLASS_FIELD],
	)
	if not reclass_rows:
		return lines, [], {}
	reclasses = {}  # original -> [reclassification entries]
	for row in reclass_rows:
		reclasses.setdefault(row[RECLASS_FIELD], []).append(row.name)
	originals = frappe.get_all(
		"Journal Entry",
		filters={"name": ("in", sorted(reclasses)), "company": company, "docstatus": 1},
		fields=["name", RECLASS_FIELD],
	)
	original_links = {row.name: row[RECLASS_FIELD] for row in originals}

	entries = set(reclasses) | {name for names in reclasses.values() for name in names}
	totals = get_entry_vat(entries, accounts)

	removed = {}  # (voucher_no, account) -> partner vouchers
	flags = {}
	for original, names in reclasses.items():
		# only the accounts the reclassification entries post VAT to; the original's other VAT accounts are untouched
		pair_accounts = {a for (v, a), vat in totals.items() if v in names and vat}
		for account in sorted(pair_accounts):
			original_vat = totals.get((original, account), 0.0)
			reclass_vat = sum(totals.get((name, account), 0.0) for name in names)
			is_full = (
				original in original_links
				and original not in names
				and original_links[original] not in names
				and original_vat != 0
				and flt(original_vat + reclass_vat, 2) == 0
			)
			if is_full:
				removed[(original, account)] = sorted(names)
				for name in names:
					removed[(name, account)] = [original]
			else:
				for name in [original, *names]:
					flags.setdefault(name, ["RECLASS_PARTIAL"])

	remaining = []
	removed_groups = {}
	for line in lines:
		partners = None
		if line.voucher_type == "Journal Entry":
			partners = removed.get((line.voucher_no, line.vat_account))
		if partners is None:
			remaining.append(line)
		else:
			removed_groups.setdefault((line.voucher_no, line.vat_account), (partners, []))[1].append(line)

	pair_rows = []
	for partners, group in removed_groups.values():
		row = get_exception_row(
			group, get_side(group[0], accounts), STATUS_RECLASSIFIED, ["VAT_RECLASSIFIED"]
		)
		row.reclass_pair = ", ".join(partners)
		pair_rows.append(row)
	flags = {name: codes for name, codes in flags.items() if name in line_entries}
	return remaining, pair_rows, flags


def get_entry_vat(voucher_nos, accounts):
	"""(voucher_no, VAT account) -> VAT of the Journal Entry on that account over all dates, with the sign of
	get_gl_lines (output: credit - debit, input: debit - credit)."""
	vat_accounts = [a for a, t in accounts.items() if t in ("Output VAT", "Input VAT")]
	if not voucher_nos or not vat_accounts:
		return {}
	rows = frappe.db.sql(
		"""
		select voucher_no, account, sum(debit) as debit, sum(credit) as credit
		from `tabGL Entry`
		where voucher_type = 'Journal Entry'
			and is_cancelled = 0
			and voucher_no in %(voucher_nos)s
			and account in %(vat_accounts)s
		group by voucher_no, account
		""",
		{"voucher_nos": sorted(voucher_nos), "vat_accounts": vat_accounts},
		as_dict=True,
	)
	totals = {}
	for row in rows:
		is_output = accounts[row.account] == "Output VAT"
		totals[(row.voucher_no, row.account)] = flt(
			row.credit - row.debit if is_output else row.debit - row.credit, 2
		)
	return totals
