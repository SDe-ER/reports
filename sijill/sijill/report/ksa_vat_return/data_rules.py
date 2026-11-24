# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""Data rules of the KSA VAT Return.

The return is built from invoices. The rules start on the date in KSA VAT Settings, "Output VAT from Sales
Invoices only, from date". Empty: the rules are off and the return works as in earlier versions on every date.
Lines before the date keep the earlier behaviour: nothing is left out, and missing data is only listed with the
status "Included (warning)".

From the date on:

Sales side (output VAT): only Sales Invoices (also credit and debit notes) count. A line of any other voucher
on the sales side is left out and listed with the status "Excluded": OUTPUT_VAT_BY_JOURNAL_ENTRY for a Journal
Entry, OUTPUT_VAT_SOURCE_NOT_ALLOWED for other vouchers, plus OUTPUT_REDUCTION_EXCLUDED when it reduces output
VAT. A Sales Invoice is never left out: VAT is collected on every taxable sale (ZATCA
Guideline for Tax Invoicing and Records under VAT Provisions v3, May 2026, section 1.3). Missing customer data is
only reported, with the status "Included (warning)". A simplified tax invoice carries no customer details
(section 4.3, Implementing Regulations Article 53).

Purchase side (input VAT): only Purchase Invoices and Journal Entries count; a line of any other voucher is left
out (INPUT_VAT_SOURCE_NOT_ALLOWED). A voucher must pass four rules or it is left out of the return and of the
detail report and listed with the status "Excluded": (a) a supplier with a name, (b) a supplier invoice number
that is real (not empty, not a placeholder such as "0", "-" or "N/A", not the system voucher number) and not used
twice by the same supplier (compared without case and without any whitespace; every copy is excluded; a Journal
Entry counts only when it debits input VAT; Purchase Invoice returns are exempt from the duplicate check because
they normally carry the number of the original invoice), (c) a valid supplier VAT number, (d) the check "Buyer details
verified". A missing attachment is only a warning. A voucher that reduces input VAT follows the same rules; when
it is excluded it also gets REDUCTION_EXCLUDED, because excluding it increases the VAT claim. Input VAT is deducted
only with a valid tax invoice in hand (same guideline, sections 9.1 and 9.4); a document received later can be
deducted in a later period (Implementing Regulations Article 49).

Settlement and opening entries are not part of the rules; they are listed with the status "Not reported".

All lookups are batched: one query per document type and rule, never one per line.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

from sijill.sijill.doctype.ksa_vat_settings.ksa_vat_settings import (
	get_ksa_vat_accounts,
	get_rules_from_date,
)
from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	EXCLUDED,
	PURCHASE_CATEGORIES,
	SALES_CATEGORIES,
	get_vat_lines,
)

# rule code -> (English text, Arabic text); both languages are always shown by the exceptions report
RULES = {
	"BILL_NO_MISSING": (
		"Supplier invoice number is missing or is a placeholder",
		"رقم فاتورة المورد غير موجود أو قيمة بديلة",
	),
	"BILL_NO_DUPLICATE": (
		"Supplier invoice number is used on more than one voucher of the same supplier",
		"رقم فاتورة المورد مكرر على أكثر من مستند للمورد نفسه",
	),
	"SUPPLIER_MISSING": ("Supplier is missing", "المورد غير موجود"),
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
		"Reduces input VAT: excluding it increases the VAT claim. Complete it.",
		"يخفض ضريبة المدخلات: استبعاده يزيد المطالبة بالضريبة. استكمله.",
	),
	"INPUT_VAT_SOURCE_NOT_ALLOWED": (
		"Input VAT only from a Purchase Invoice or a Journal Entry",
		"ضريبة المدخلات من فاتورة مشتريات أو قيد يومية فقط",
	),
	"OUTPUT_VAT_SOURCE_NOT_ALLOWED": (
		"Output VAT only from a Sales Invoice",
		"ضريبة المخرجات من فاتورة مبيعات فقط",
	),
	"OUTPUT_REDUCTION_EXCLUDED": (
		"Reduces output VAT: excluding it increases the VAT due. Issue a credit note instead.",
		"يخفض ضريبة المخرجات: استبعاده يزيد الضريبة المستحقة. أصدر إشعار دائن بدلاً منه.",
	),
	"OUTPUT_VAT_BY_JOURNAL_ENTRY": (
		"Output VAT posted by Journal Entry - not allowed",
		"ضريبة مخرجات مسجلة بقيد يومية - غير مسموح",
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
	"NOT_A_TAXABLE_TRANSACTION": (
		"Not a taxable transaction: settlement, VAT payment or opening entry",
		"ليست عملية خاضعة للضريبة: تسوية أو سداد ضريبة أو قيد افتتاحي",
	),
}

PURCHASE_RULES = (
	"BILL_NO_MISSING",
	"BILL_NO_DUPLICATE",
	"SUPPLIER_MISSING",
	"SUPPLIER_VAT_INVALID",
	"BUYER_DETAILS_NOT_VERIFIED",
	"ATTACHMENT_MISSING",
)

# supplier invoice numbers that mean "none" (compared after normalise_bill_no)
BILL_NO_PLACEHOLDERS = frozenset(
	re.sub(r"\s+", "", value).casefold()
	for value in ("0", "-", "--", ".", "N/A", "NA", "none", "لا يوجد", "بدون")
)

# 15 digits, starts and ends with 3
VAT_NUMBER_PATTERN = re.compile(r"^3[0-9]{13}3$")

BUYER_FIELD = "sijill_buyer_details_verified"
ADDITIONAL_IDS_FIELD = "custom_additional_ids"

STATUS_EXCLUDED = "Excluded"
STATUS_WARNING = "Included (warning)"
STATUS_NOT_REPORTED = "Not reported"

# voucher types that may carry input VAT from the cutoff date on
INPUT_VAT_SOURCES = ("Purchase Invoice", "Journal Entry")

# the supplier invoice number field of each voucher type
BILL_FIELDS = {"Purchase Invoice": "bill_no", "Journal Entry": "bill_no", "Payment Entry": "reference_no"}


def normalise_bill_no(value):
	"""A supplier invoice number without case and without any whitespace, for comparisons."""
	return re.sub(r"\s+", "", value or "").casefold()


def is_bill_no_missing(bill_no, voucher_no):
	"""Empty, a placeholder (BILL_NO_PLACEHOLDERS) or the system voucher number."""
	value = normalise_bill_no(bill_no)
	return not value or value in BILL_NO_PLACEHOLDERS or value == normalise_bill_no(voucher_no)


def get_rule_result(filters):
	"""(included_lines, exception_rows) of the KSA VAT Return lines for the filters (company, from_date,
	to_date)."""
	filters = frappe._dict(filters)
	return evaluate_lines(get_vat_lines(filters, include_excluded=True), filters.company)


def evaluate_lines(lines, company):
	"""Apply the rules to lines from get_vat_lines(include_excluded=True).

	Returns (included_lines, exception_rows). included_lines are the lines of the return; their bill_no,
	party_name and tax_id are filled (a marker where the data is missing). exception_rows has one row per
	voucher and side that is excluded, warned about or not reported.
	"""
	accounts = get_ksa_vat_accounts(company)
	cutoff = get_rules_from_date(company)
	groups = {}
	for line in lines:
		not_reported = line.category == EXCLUDED
		side = get_side(line, accounts)
		groups.setdefault((line.voucher_type, line.voucher_no, side, not_reported), []).append(line)

	def rules_apply(group):
		return cutoff is not None and getdate(group[0].posting_date) >= cutoff

	def is_sales_source_allowed(key, group):
		return key[0] == "Sales Invoice" or not rules_apply(group)

	def is_purchase_source_allowed(key, group):
		return key[0] in INPUT_VAT_SOURCES or not rules_apply(group)

	purchase_keys = [
		k
		for k, v in groups.items()
		if v[0].category in PURCHASE_CATEGORIES and is_purchase_source_allowed(k, v)
	]
	sales_keys = [
		k for k, v in groups.items() if v[0].category in SALES_CATEGORIES and is_sales_source_allowed(k, v)
	]
	purchase_set, sales_set = set(purchase_keys), set(sales_keys)
	purchases = PurchaseFacts(company, accounts, purchase_keys, groups)
	sales = SalesFacts(sales_keys, groups)

	included = []
	exceptions = []
	for key, group in groups.items():
		first = group[0]
		vat = flt(sum(flt(line.vat_amount) for line in group), 2)
		if first.category == EXCLUDED:
			exceptions.append(
				get_exception_row(group, key[2], STATUS_NOT_REPORTED, ["NOT_A_TAXABLE_TRANSACTION"])
			)
		elif first.category in PURCHASE_CATEGORIES:
			if key not in purchase_set:
				codes = ["INPUT_VAT_SOURCE_NOT_ALLOWED"] + (["REDUCTION_EXCLUDED"] if vat < 0 else [])
				exceptions.append(get_exception_row(group, key[2], STATUS_EXCLUDED, codes))
				continue
			codes, details = purchases.check(key, group)
			blocking = [code for code in codes if code != "ATTACHMENT_MISSING"]
			if blocking and rules_apply(group):
				row = get_exception_row(
					group, key[2], STATUS_EXCLUDED, codes + (["REDUCTION_EXCLUDED"] if vat < 0 else [])
				)
				row.update({k: v for k, v in details.items() if v})
				exceptions.append(row)
				continue
			if codes:
				row = get_exception_row(group, key[2], STATUS_WARNING, codes)
				row.update({k: v for k, v in details.items() if v})
				exceptions.append(row)
			# display only: the value of the line (for example the bank name, or a Journal Entry's cheque number)
			# comes before the marker
			marker = get_marker()
			own = {"bill_no": first.bill_no, "party_name": first.party_name}
			details = {k: v or (own.get(k) or "").strip() or marker for k, v in details.items()}
			for line in group:
				line.update(details)
			included += group
		else:
			if key not in sales_set:
				codes = [
					"OUTPUT_VAT_BY_JOURNAL_ENTRY"
					if key[0] == "Journal Entry"
					else "OUTPUT_VAT_SOURCE_NOT_ALLOWED"
				]
				if vat < 0:
					codes.append("OUTPUT_REDUCTION_EXCLUDED")
				exceptions.append(get_exception_row(group, key[2], STATUS_EXCLUDED, codes))
				continue
			codes, details = sales.check(key, group)
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
	)
	return row


def get_marker():
	return _("Missing - see VAT Documents Requiring Completion")


def is_valid_vat_number(value):
	return bool(VAT_NUMBER_PATTERN.match((value or "").strip()))


def get_records(doctype, names, fields):
	"""name -> record for the given names, in one query. Permissions are not applied on purpose: the reports
	check the report roles and the Company permission (validate_filters), the rules need the facts of every
	voucher in the period to give the same result for every user, and the 0.1.4 tax ID lookup did the same."""
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
		against = {
			doc.return_against
			for doc in self.docs.get("Purchase Invoice", {}).values()
			if doc.get("is_return") and doc.get("return_against")
		}
		self.against = get_records(
			"Purchase Invoice",
			against,
			[
				"bill_no",
				*([BUYER_FIELD] if frappe.get_meta("Purchase Invoice").has_field(BUYER_FIELD) else []),
			],
		)
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
			fields += ["supplier", "supplier_name", "is_return", "return_against"]
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
			if is_bill_no_missing(row.bill_no, row.name):
				continue
			add_bill_key(keys, row.supplier, row.bill_no, "Purchase Invoice", row.name)

		input_accounts = [a for a, t in accounts.items() if t == "Input VAT"]
		if input_accounts:
			# a Journal Entry counts only when it debits input VAT: a reversal or correction (net credit) is not
			# a second copy of the supplier invoice
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
					and (
						select ifnull(sum(v.debit - v.credit), 0) from `tabJournal Entry Account` v
						where v.parent = je.name and v.account in %(input_accounts)s
					) > 0
				""",
				{"company": company, "suppliers": sorted(suppliers), "input_accounts": input_accounts},
				as_dict=True,
			)
			for row in entries:
				if not is_bill_no_missing(row.bill_no, row.name):
					add_bill_key(keys, row.party, row.bill_no, "Journal Entry", row.name)
		return keys

	def check(self, key, group):
		"""(failed rule codes, details to put on the lines) of one purchase voucher."""
		voucher_type, voucher_no = key[0], key[1]
		first = group[0]
		doc = self.docs.get(voucher_type, {}).get(voucher_no) or {}
		supplier = first.party if first.party_type == "Supplier" and first.party else None
		master = self.suppliers.get(supplier) or {}

		is_return = voucher_type == "Purchase Invoice" and bool(doc.get("is_return"))
		against = self.against.get(doc.get("return_against")) or {} if is_return else {}

		bill_field = BILL_FIELDS.get(voucher_type)
		bill_no = (doc.get(bill_field) or "").strip() if bill_field else ""
		if is_return and is_bill_no_missing(bill_no, voucher_no):
			# a return normally carries the number of the original invoice
			bill_no = (against.get("bill_no") or "").strip() or bill_no
		if voucher_type == "Purchase Invoice":
			supplier_name = (doc.get("supplier_name") or "").strip()
		else:
			supplier_name = (master.get("supplier_name") or "").strip()
		tax_id = (master.get("tax_id") or "").strip()

		failed = set()
		if bill_field is None:
			# no supplier invoice number field on this voucher type (for example Expense Claim): rule a is skipped
			pass
		elif is_bill_no_missing(bill_no, voucher_no):
			failed.add("BILL_NO_MISSING")
		elif supplier and not is_return:
			holders = self.bill_keys.get((supplier, normalise_bill_no(bill_no)), set()) | {
				(voucher_type, voucher_no)
			}
			if len(holders) > 1:
				failed.add("BILL_NO_DUPLICATE")
		if not supplier or not supplier_name:
			failed.add("SUPPLIER_MISSING")
		if not is_valid_vat_number(tax_id):
			failed.add("SUPPLIER_VAT_INVALID")
		# required on every input VAT source (Purchase Invoice, Journal Entry); fails safe when the field is missing
		if voucher_type in INPUT_VAT_SOURCES and not (
			doc.get(BUYER_FIELD) or (is_return and against.get(BUYER_FIELD))
		):
			failed.add("BUYER_DETAILS_NOT_VERIFIED")
		if voucher_no not in self.attached.get(voucher_type, set()):
			failed.add("ATTACHMENT_MISSING")

		codes = [code for code in PURCHASE_RULES if code in failed]
		return codes, {"bill_no": bill_no, "party_name": supplier_name, "tax_id": tax_id}


def add_bill_key(keys, supplier, bill_no, voucher_type, voucher_no):
	keys.setdefault((supplier, normalise_bill_no(bill_no)), set()).add((voucher_type, voucher_no))


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
			"party_name": name or (first.party_name or "").strip() or marker,
			"tax_id": tax_id or other_id or marker,
		}
		return codes, details
