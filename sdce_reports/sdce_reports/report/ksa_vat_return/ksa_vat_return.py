# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""KSA VAT Return.

Lays out the Saudi VAT return (fields 1 to 16) from submitted invoices and from other
vouchers posted to the VAT accounts set in KSA VAT Settings. The same transaction lines
feed the KSA VAT Return Detail report, so every amount here can be traced to its vouchers.

Sources
- Sales and Purchase Invoices: item level taxable amount and VAT from Item Wise Tax Detail,
  for tax rows posted to an Output VAT (sales) or Input VAT (purchases) account. Returns and
  debit notes go to the Adjustment column.
- Any other voucher (Journal Entry, Payment Entry, ...) posting to an Output or Input VAT
  account. The taxable amount is derived from the VAT and the account's Tax Rate.

Not reported
- Vouchers whose GL entries only move amounts between the configured VAT accounts (closing a
  return into the VAT Settlement account, paying it, reclassifications).
- Opening entries.
Both are listed by the detail report when "Show Excluded Entries" is set.
"""

import frappe
from erpnext import get_region
from erpnext.accounts.report.utils import validate_date_range
from frappe import _
from frappe.utils import flt, getdate

from sdce_reports.sdce_reports.doctype.ksa_vat_settings.ksa_vat_settings import get_ksa_vat_accounts

STANDARD_RATED_SALES = "Standard Rated Sales"
ZERO_RATED_SALES = "Zero Rated Domestic Sales"
EXPORTS = "Exports"
STANDARD_RATED_PURCHASES = "Standard Rated Purchases"
ZERO_RATED_PURCHASES = "Zero Rated Purchases"
EXCLUDED = "Excluded"

SALES_CATEGORIES = (STANDARD_RATED_SALES, ZERO_RATED_SALES, EXPORTS)
PURCHASE_CATEGORIES = (STANDARD_RATED_PURCHASES, ZERO_RATED_PURCHASES)

# rates shown as separate lines even when nothing was charged at that rate
DEFAULT_RATES = (15.0, 5.0)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	lines = get_vat_lines(filters)
	currency, tax_id = frappe.get_cached_value("Company", filters.company, ["default_currency", "tax_id"])
	data = get_data(lines)
	for row in data:
		row["currency"] = currency
		row["company_tax_id"] = tax_id
	return get_columns(), data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"), title=_("Missing Company"))
	frappe.has_permission("Company", doc=filters.company, throw=True)
	validate_date_range(filters)

	if get_region(filters.company) != "Saudi Arabia":
		frappe.throw(
			_(
				"The company {0} is not in Saudi Arabia. The KSA VAT Return is only available for companies in Saudi Arabia."
			).format(frappe.bold(filters.company))
		)

	if not get_ksa_vat_accounts(filters.company):
		frappe.throw(
			_("Set the VAT accounts of company {0} in {1} first.").format(
				frappe.bold(filters.company),
				frappe.utils.get_link_to_form("KSA VAT Settings", filters.company),
			),
			title=_("KSA VAT Settings Missing"),
		)


def get_columns():
	return [
		{"fieldname": "no", "label": _("No"), "fieldtype": "Data", "width": 50},
		{"fieldname": "legend", "label": _("Description"), "fieldtype": "Data", "width": 420},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "adjustment",
			"label": _("Adjustment"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
	]


# ------------------------------------------------------------------------------------------
# Return layout
# ------------------------------------------------------------------------------------------


def get_data(lines):
	data = []

	def total(categories, rate=None, with_vat=True):
		amount = adjustment = vat = 0.0
		for line in lines:
			if line.category not in categories:
				continue
			if rate is not None and flt(line.rate) != rate:
				continue
			if line.is_adjustment:
				adjustment += flt(line.taxable_amount)
			else:
				amount += flt(line.taxable_amount)
			vat += flt(line.vat_amount)
		return {
			"amount": flt(amount, 2),
			"adjustment": flt(adjustment, 2),
			"vat_amount": flt(vat, 2) if with_vat else None,
		}

	def append(no, legend, values=None, category=None, rate=None, side=None, bold=0, heading=0):
		row = {
			"no": no,
			"legend": legend,
			"amount": None,
			"adjustment": None,
			"vat_amount": None,
			"category": category,
			"rate": rate,
			"side": side,
			"bold": bold,
			"is_heading": heading,
		}
		row.update(values or {})
		data.append(row)
		return row

	def zero_only(values):
		"""Fields that only report an amount (zero rated, exports)."""
		return {"amount": values["amount"], "adjustment": values["adjustment"], "vat_amount": None}

	sales_rates = get_rates(lines, (STANDARD_RATED_SALES,))
	purchase_rates = get_rates(lines, (STANDARD_RATED_PURCHASES,))

	# VAT on sales
	append("", _("VAT on Sales"), heading=1)
	for rate in sales_rates:
		append(
			"",
			_("Standard rated sales at {0}%").format(frappe.format(rate, {"fieldtype": "Float"})),
			total((STANDARD_RATED_SALES,), rate),
			category=STANDARD_RATED_SALES,
			rate=rate,
			side="Sales",
		)
	standard_sales = total((STANDARD_RATED_SALES,))
	append("1", _("Standard rated sales"), standard_sales, category=STANDARD_RATED_SALES, side="Sales")
	append("2", _("Private healthcare and private education sales to citizens"))
	append(
		"3",
		_("Zero rated domestic sales"),
		zero_only(total((ZERO_RATED_SALES,), with_vat=False)),
		category=ZERO_RATED_SALES,
		side="Sales",
	)
	append("4", _("Exports"), zero_only(total((EXPORTS,), with_vat=False)), category=EXPORTS, side="Sales")
	append("5", _("Exempt sales"), {"amount": 0.0})
	total_sales = total(SALES_CATEGORIES)
	append("6", _("Total sales"), total_sales, side="Sales", bold=1)

	# VAT on purchases
	append("", _("VAT on Purchases"), heading=1)
	for rate in purchase_rates:
		append(
			"",
			_("Standard rated purchases at {0}%").format(frappe.format(rate, {"fieldtype": "Float"})),
			total((STANDARD_RATED_PURCHASES,), rate),
			category=STANDARD_RATED_PURCHASES,
			rate=rate,
			side="Purchase",
		)
	standard_purchases = total((STANDARD_RATED_PURCHASES,))
	append(
		"7",
		_("Standard rated domestic purchases"),
		standard_purchases,
		category=STANDARD_RATED_PURCHASES,
		side="Purchase",
	)
	append("8", _("Imports subject to VAT paid at customs"))
	append("9", _("Imports subject to VAT accounted for through the reverse charge mechanism"))
	append(
		"10",
		_("Zero rated purchases"),
		zero_only(total((ZERO_RATED_PURCHASES,), with_vat=False)),
		category=ZERO_RATED_PURCHASES,
		side="Purchase",
	)
	append("11", _("Exempt purchases"), {"amount": 0.0})
	total_purchases = total(PURCHASE_CATEGORIES)
	append("12", _("Total purchases"), total_purchases, side="Purchase", bold=1)

	# VAT due
	net_vat = flt(total_sales["vat_amount"] - total_purchases["vat_amount"], 2)
	append("", _("VAT Due"), heading=1)
	append("13", _("Total VAT due for current period"), {"vat_amount": net_vat}, side="All", bold=1)
	append("14", _("Corrections from previous period (between SAR ±5,000)"), {"vat_amount": 0.0})
	append("15", _("VAT credit carried forward from previous period(s)"), {"vat_amount": 0.0})
	append("16", _("Net VAT due (or claim)"), {"vat_amount": net_vat}, side="All", bold=1)

	return data


def get_rates(lines, categories):
	rates = {flt(line.rate) for line in lines if line.category in categories and flt(line.rate)}
	rates.update(DEFAULT_RATES)
	return sorted(rates, reverse=True)


# ------------------------------------------------------------------------------------------
# Transaction lines (shared with KSA VAT Return Detail)
# ------------------------------------------------------------------------------------------


def get_vat_lines(filters, include_excluded=False):
	"""Returns one line per voucher, VAT category, rate and adjustment flag.

	Each line: posting_date, voucher_type, voucher_no, party_type, party, party_name, bill_no,
	bill_date, category, rate, is_adjustment, taxable_amount, vat_amount, vat_account, remarks.
	"""
	accounts = get_ksa_vat_accounts(filters.company)
	output_accounts = [a for a, t in accounts.items() if t == "Output VAT"]
	input_accounts = [a for a, t in accounts.items() if t == "Input VAT"]

	lines = []
	if output_accounts:
		lines += get_invoice_lines(filters, "Sales Invoice", output_accounts)
	if input_accounts:
		lines += get_invoice_lines(filters, "Purchase Invoice", input_accounts)
	if output_accounts or input_accounts:
		lines += get_gl_lines(filters, accounts, include_excluded)

	lines.sort(key=lambda d: (getdate(d.posting_date), d.voucher_type, d.voucher_no))
	return lines


# The taxable amount of an item is counted once per rate, even if the item carries more than one
# tax row at that rate on the VAT accounts.
SALES_INVOICE_QUERY = """
		select
			inv.name as voucher_no, inv.posting_date, inv.customer as party,
			inv.customer_name as party_name, inv.name as bill_no, inv.posting_date as bill_date, addr.country as party_country,
			(inv.is_return = 1 or inv.is_debit_note = 1) as is_adjustment, item.rate,
			sum(item.taxable_amount) as taxable_amount, sum(item.vat_amount) as vat_amount,
			group_concat(distinct item.accounts separator ', ') as vat_account
		from (
			select d.parent, d.item_row, d.rate,
				max(d.taxable_amount) as taxable_amount, sum(d.amount) as vat_amount,
				group_concat(distinct tax.account_head separator ', ') as accounts
			from `tabItem Wise Tax Detail` d
			inner join `tabSales Taxes and Charges` tax on tax.name = d.tax_row
			where d.parenttype = %(doctype)s
				and tax.account_head in %(vat_accounts)s
			group by d.parent, d.item_row, d.rate
		) item
		inner join `tabSales Invoice` inv on inv.name = item.parent
		left join `tabAddress` addr on addr.name = inv.customer_address
		where inv.docstatus = 1
			and inv.company = %(company)s
			and inv.posting_date between %(from_date)s and %(to_date)s
		group by inv.name, item.rate, is_adjustment
"""

PURCHASE_INVOICE_QUERY = """
		select
			inv.name as voucher_no, inv.posting_date, inv.supplier as party,
			inv.supplier_name as party_name, inv.bill_no as bill_no, inv.bill_date as bill_date, null as party_country,
			inv.is_return = 1 as is_adjustment, item.rate,
			sum(item.taxable_amount) as taxable_amount, sum(item.vat_amount) as vat_amount,
			group_concat(distinct item.accounts separator ', ') as vat_account
		from (
			select d.parent, d.item_row, d.rate,
				max(d.taxable_amount) as taxable_amount, sum(d.amount) as vat_amount,
				group_concat(distinct tax.account_head separator ', ') as accounts
			from `tabItem Wise Tax Detail` d
			inner join `tabPurchase Taxes and Charges` tax on tax.name = d.tax_row
			where d.parenttype = %(doctype)s
				and tax.account_head in %(vat_accounts)s
				and tax.add_deduct_tax = 'Add'
				and tax.category in ('Total', 'Valuation and Total')
			group by d.parent, d.item_row, d.rate
		) item
		inner join `tabPurchase Invoice` inv on inv.name = item.parent
		where inv.docstatus = 1
			and inv.company = %(company)s
			and inv.posting_date between %(from_date)s and %(to_date)s
		group by inv.name, item.rate, is_adjustment
"""


def get_invoice_lines(filters, doctype, vat_accounts):
	is_sales = doctype == "Sales Invoice"
	rows = frappe.db.sql(
		SALES_INVOICE_QUERY if is_sales else PURCHASE_INVOICE_QUERY,
		{
			"doctype": doctype,
			"vat_accounts": vat_accounts,
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
		},
		as_dict=True,
	)

	company_country = frappe.get_cached_value("Company", filters.company, "country")
	lines = []
	for row in rows:
		rate = flt(row.rate)
		if is_sales:
			if rate:
				category = STANDARD_RATED_SALES
			elif row.party_country and row.party_country != company_country:
				category = EXPORTS
			else:
				category = ZERO_RATED_SALES
		else:
			category = STANDARD_RATED_PURCHASES if rate else ZERO_RATED_PURCHASES

		lines.append(
			frappe._dict(
				posting_date=row.posting_date,
				voucher_type=doctype,
				voucher_no=row.voucher_no,
				party_type="Customer" if is_sales else "Supplier",
				party=row.party,
				party_name=row.party_name,
				bill_no=row.bill_no,
				bill_date=row.bill_date,
				category=category,
				rate=rate,
				is_adjustment=row.is_adjustment,
				taxable_amount=flt(row.taxable_amount, 2),
				vat_amount=flt(row.vat_amount, 2),
				vat_account=row.vat_account,
				remarks=None,
			)
		)
	return lines


def get_gl_lines(filters, accounts, include_excluded=False):
	"""Lines for vouchers other than Sales and Purchase Invoices posted to the VAT accounts."""
	vat_accounts = [a for a, t in accounts.items() if t in ("Output VAT", "Input VAT")]
	rows = frappe.db.sql(
		"""
		select
			g.voucher_type, g.voucher_no, min(g.posting_date) as posting_date, g.account,
			sum(g.debit) as debit, sum(g.credit) as credit,
			max(g.is_opening = 'Yes') as is_opening,
			exists(
				select 1 from `tabGL Entry` o
				where o.voucher_type = g.voucher_type and o.voucher_no = g.voucher_no
					and o.is_cancelled = 0 and o.account not in %(all_accounts)s
			) as has_other_accounts
		from `tabGL Entry` g
		where g.company = %(company)s
			and g.is_cancelled = 0
			and g.posting_date between %(from_date)s and %(to_date)s
			and g.account in %(vat_accounts)s
			and g.voucher_type not in ('Sales Invoice', 'Purchase Invoice')
		group by g.voucher_type, g.voucher_no, g.account
		""",
		{
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"vat_accounts": vat_accounts,
			"all_accounts": list(accounts),
		},
		as_dict=True,
	)

	lines = []
	for row in rows:
		is_output = accounts[row.account] == "Output VAT"
		vat_amount = flt(row.credit - row.debit if is_output else row.debit - row.credit, 2)
		if not vat_amount:
			continue

		remarks = None
		if row.is_opening:
			remarks = _("Opening entry")
		elif not row.has_other_accounts:
			remarks = _("Only moves amounts between VAT accounts (settlement or reclassification)")

		if remarks and not include_excluded:
			continue

		rate = flt(frappe.get_cached_value("Account", row.account, "tax_rate"))
		taxable_amount = flt(vat_amount * 100 / rate, 2) if rate else 0.0
		if remarks:
			category = EXCLUDED
		elif is_output:
			category = STANDARD_RATED_SALES if rate else ZERO_RATED_SALES
		else:
			category = STANDARD_RATED_PURCHASES if rate else ZERO_RATED_PURCHASES

		party_type, party = get_voucher_party(row.voucher_type, row.voucher_no, is_output)
		bill_no, bill_date = get_voucher_reference(row.voucher_type, row.voucher_no)
		lines.append(
			frappe._dict(
				posting_date=row.posting_date,
				voucher_type=row.voucher_type,
				voucher_no=row.voucher_no,
				party_type=party_type,
				party=party,
				party_name=get_party_name(party_type, party),
				bill_no=bill_no,
				bill_date=bill_date,
				category=category,
				rate=rate,
				is_adjustment=1 if vat_amount < 0 else 0,
				taxable_amount=taxable_amount,
				vat_amount=vat_amount,
				vat_account=row.account,
				remarks=remarks,
			)
		)
	return lines


def get_voucher_party(voucher_type, voucher_no, is_output):
	preferred = "Customer" if is_output else "Supplier"
	parties = frappe.get_all(
		"GL Entry",
		filters={
			"voucher_type": voucher_type,
			"voucher_no": voucher_no,
			"is_cancelled": 0,
			"party_type": ("in", ["Customer", "Supplier"]),
			"party": ("is", "set"),
		},
		fields=["party_type", "party"],
		distinct=True,
	)
	parties.sort(key=lambda d: d.party_type != preferred)
	if parties:
		return parties[0].party_type, parties[0].party
	return None, None


def get_voucher_reference(voucher_type, voucher_no):
	if voucher_type == "Journal Entry":
		bill_no, cheque_no, bill_date, cheque_date = frappe.db.get_value(
			"Journal Entry", voucher_no, ["bill_no", "cheque_no", "bill_date", "cheque_date"]
		)
		return bill_no or cheque_no, bill_date or cheque_date
	if voucher_type == "Payment Entry":
		return frappe.db.get_value("Payment Entry", voucher_no, ["reference_no", "reference_date"])
	return None, None


def get_party_name(party_type, party):
	if not party_type or not party:
		return None
	field = "customer_name" if party_type == "Customer" else "supplier_name"
	return frappe.get_cached_value(party_type, party, field)
