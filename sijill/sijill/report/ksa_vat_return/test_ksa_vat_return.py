# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import frappe
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import add_days, flt, nowdate

from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	EXCLUDED,
	EXPORTS,
	STANDARD_RATED_PURCHASES,
	STANDARD_RATED_SALES,
	ZERO_RATED_SALES,
	execute,
	group_by_effective_rate,
)
from sijill.sijill.report.ksa_vat_return_detail.ksa_vat_return_detail import (
	execute as execute_detail,
)
from sijill.sijill.report.vat_documents_requiring_completion.vat_documents_requiring_completion import (
	execute as execute_exceptions,
)

COMPANY = "_Test KSA VAT Company"
ABBR = "_TKV"
OUTPUT_VAT = f"Output VAT 15% - {ABBR}"
INPUT_VAT = f"Input VAT 15% - {ABBR}"
VAT_PAYABLE = f"VAT Payable - {ABBR}"
CUSTOMER = "_Test KSA VAT Customer"
EXPORT_CUSTOMER = "_Test KSA VAT Export Customer"
SUPPLIER = "_Test KSA VAT Supplier"
ITEM = "_Test KSA VAT Item"


class TestKSAVATReturn(ERPNextTestSuite):
	def setUp(self):
		make_company()
		make_vat_accounts()
		make_settings()
		make_parties()
		make_item()

	def filters(self, **extra):
		return {"company": COMPANY, "from_date": nowdate(), "to_date": nowdate(), **extra}

	def summary(self):
		_columns, data = execute(self.filters())
		return {row["no"]: row for row in data if row["no"]}, data

	def exceptions(self, **extra):
		_columns, rows = execute_exceptions(self.filters(**extra))
		return {row["voucher_no"]: row for row in rows}

	def test_company_outside_saudi_arabia_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"company": "_Test Company", "from_date": nowdate(), "to_date": nowdate()},
		)

	def test_missing_settings_are_rejected(self):
		frappe.delete_doc("KSA VAT Settings", COMPANY, force=True)
		self.assertRaises(frappe.ValidationError, execute, self.filters())

	def test_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts User")
		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, execute, self.filters())

	def test_return_fields(self):
		si = make_sales_invoice(rate=1000)
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.items[0].qty = -1
		credit_note.items[0].rate = 200
		credit_note.submit()
		make_sales_invoice(rate=300, vat_rate=0)
		make_sales_invoice(rate=400, vat_rate=0, customer=EXPORT_CUSTOMER)
		make_purchase_invoice(rate=500, bill_no="SUP-0001")
		set_cutoff(add_days(nowdate(), 30))
		make_vat_journal_entry(net=100)
		make_settlement_journal_entry()

		boxes, data = self.summary()

		self.assertEqual(
			(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (1100, -200, 135)
		)
		self.assertEqual(boxes["3"]["amount"], 300)
		self.assertIsNone(boxes["3"]["vat_amount"])
		self.assertEqual(boxes["4"]["amount"], 400)
		self.assertEqual((boxes["6"]["amount"], boxes["6"]["vat_amount"]), (1800, 135))
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (500, 75))
		self.assertEqual(boxes["13"]["vat_amount"], 60)
		self.assertEqual(boxes["16"]["vat_amount"], 60)
		self.assertEqual(data[0]["currency"], "SAR")

		# the settlement entry closes the period and is not a taxable transaction
		self.assertEqual(boxes["12"]["vat_amount"], 75)

	def test_detail_reconciles_with_summary(self):
		si = make_sales_invoice(rate=1000)
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.items[0].qty = -1
		credit_note.submit()
		make_sales_invoice(rate=400, vat_rate=0, customer=EXPORT_CUSTOMER)
		make_purchase_invoice(rate=500, bill_no="SUP-0002")
		set_cutoff(add_days(nowdate(), 30))
		make_vat_journal_entry(net=100)

		boxes, _data = self.summary()
		_columns, lines = execute_detail(self.filters())

		def total(categories, field):
			return sum(line[field] for line in lines if line["category"] in categories)

		self.assertEqual(total((STANDARD_RATED_SALES,), "vat_amount"), boxes["1"]["vat_amount"])
		self.assertEqual(
			total((STANDARD_RATED_SALES,), "taxable_amount"), boxes["1"]["amount"] + boxes["1"]["adjustment"]
		)
		self.assertEqual(total((EXPORTS,), "taxable_amount"), boxes["4"]["amount"])
		self.assertEqual(total((STANDARD_RATED_PURCHASES,), "vat_amount"), boxes["7"]["vat_amount"])

		purchase = next(line for line in lines if line["voucher_type"] == "Purchase Invoice")
		self.assertEqual(purchase["bill_no"], "SUP-0002")
		self.assertEqual(purchase["party_name"], SUPPLIER)
		self.assertEqual(purchase["tax_id"], "300000000000003")
		self.assertEqual(purchase["grand_total"], 575)

		journal = next(line for line in lines if line["voucher_type"] == "Journal Entry")
		self.assertEqual((journal["taxable_amount"], journal["vat_amount"]), (100, 15))
		self.assertEqual(journal["party"], CUSTOMER)

	def test_detail_filters_and_excluded_entries(self):
		make_sales_invoice(rate=1000)
		make_sales_invoice(rate=300, vat_rate=0)
		make_purchase_invoice(rate=500, bill_no="SUP-0003")
		make_settlement_journal_entry()

		_columns, lines = execute_detail(self.filters(side="Purchase"))
		self.assertEqual({line["category"] for line in lines}, {STANDARD_RATED_PURCHASES})

		_columns, lines = execute_detail(self.filters(category=ZERO_RATED_SALES))
		self.assertEqual([line["taxable_amount"] for line in lines], [300])

		_columns, lines = execute_detail(self.filters())
		self.assertNotIn(EXCLUDED, {line["category"] for line in lines})

		# the settlement entry is not part of the detail; the exceptions report lists it only on request
		self.assertEqual(
			[row for row in self.exceptions().values() if row["voucher_type"] == "Journal Entry"], []
		)
		_columns, rows = execute_exceptions(self.filters(show_not_reported=1))
		settlement = [row for row in rows if row["voucher_type"] == "Journal Entry"]
		self.assertEqual({row["side"] for row in settlement}, {"Sales", "Purchase"})
		self.assertEqual({row["status"] for row in settlement}, {"Not reported"})
		self.assertEqual({row["failed_codes"] for row in settlement}, {"NOT_A_TAXABLE_TRANSACTION"})

	def test_vat_payment_through_a_vat_account_is_not_reported(self):
		"""Paying the authority straight from an Output VAT account is a settlement, not a sale."""
		make_sales_invoice(rate=1000)
		bank = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0}, "name"
		)
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": COMPANY,
				"posting_date": nowdate(),
				"cheque_no": "SADAD-1",
				"cheque_date": nowdate(),
				"accounts": [
					{
						"account": OUTPUT_VAT,
						"debit_in_account_currency": 150,
						"cost_center": f"Main - {ABBR}",
					},
					{"account": bank, "credit_in_account_currency": 150, "cost_center": f"Main - {ABBR}"},
				],
			}
		)
		je.insert()
		je.submit()

		boxes, _data = self.summary()
		self.assertEqual((boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (0, 150))

		_columns, lines = execute_detail(self.filters(voucher_type="Journal Entry"))
		self.assertEqual(lines, [])
		_columns, rows = execute_exceptions(self.filters(show_not_reported=1))
		self.assertEqual(
			[(row["status"], row["vat_amount"]) for row in rows if row["voucher_type"] == "Journal Entry"],
			[("Not reported", -150)],
		)

	def test_vat_charged_by_the_bank_is_excluded(self):
		"""Input VAT a bank charges on its fees (Dr Input VAT, Cr Bank) is a purchase, not a settlement. It has
		no supplier and no invoice data, so the data rules leave it out and the exceptions report lists it."""
		set_cutoff(add_days(nowdate(), -400))
		bank = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0}, "name"
		)
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": COMPANY,
				"posting_date": nowdate(),
				"accounts": [
					{"account": INPUT_VAT, "debit_in_account_currency": 30, "cost_center": f"Main - {ABBR}"},
					{"account": bank, "credit_in_account_currency": 30, "cost_center": f"Main - {ABBR}"},
				],
			}
		)
		je.insert()
		je.submit()

		boxes, _data = self.summary()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))
		row = self.exceptions()[je.name]
		self.assertEqual((row["side"], row["status"], row["vat_amount"]), ("Purchase", "Excluded", 30))
		self.assertEqual(
			row["failed_codes"].split("; "),
			[
				"BILL_NO_MISSING",
				"SUPPLIER_MISSING",
				"SUPPLIER_VAT_INVALID",
				"BUYER_DETAILS_NOT_VERIFIED",
				"ATTACHMENT_MISSING",
			],
		)

	def test_actual_vat_row_is_standard_rated(self):
		"""A VAT row of charge type "Actual" stores rate 0 in Item Wise Tax Detail; the line still carries VAT
		and belongs in field 7 at the 15% rate, not in the zero rated field 10."""
		make_purchase_invoice(rate=869.57, bill_no="SUP-ACT-1", actual_vat=130.44)

		boxes, _data = self.summary()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (869.57, 130.44))
		self.assertEqual(boxes["10"]["amount"], 0)
		self.assertEqual(boxes["12"]["vat_amount"], 130.44)
		self.assertEqual(boxes["13"]["vat_amount"], -130.44)

		_columns, lines = execute_detail(self.filters(voucher_type="Purchase Invoice"))
		self.assertEqual(
			[(line["category"], line["rate"]) for line in lines], [(STANDARD_RATED_PURCHASES, 15)]
		)

	def test_actual_row_next_to_a_rate_row_is_counted_once(self):
		"""One item with a 15% row and an "Actual" row on the VAT account: both map to 15%, the item's taxable amount
		is counted once (review of #20). Built from Item Wise Tax Detail rows directly."""
		lines = group_by_effective_rate(
			[
				invoice_row(item_row="r1", rate=15, taxable=1000, vat=150),
				invoice_row(item_row="r1", rate=0, taxable=1000, vat=5),
				invoice_row(item_row="r2", rate=15, taxable=200, vat=30),
			]
		)
		self.assertEqual(
			[(line.rate, line.taxable_amount, line.vat_amount) for line in lines.values()], [(15, 1200, 185)]
		)

	def test_actual_row_without_account_tax_rate(self):
		"""VAT account without a Tax Rate: an "Actual" row next to a 15% row of the same item takes the item's 15%
		(no second line at the 0.5% the Actual amount alone implies); an Actual-only item takes the implied rate
		snapped to 15%; an odd implied rate stays as it is, rounded."""
		frappe.db.set_value("Account", INPUT_VAT, "tax_rate", 0)
		frappe.clear_cache()
		lines = group_by_effective_rate(
			[
				invoice_row(item_row="r1", rate=15, taxable=1000, vat=150),
				invoice_row(item_row="r1", rate=0, taxable=1000, vat=5),
				invoice_row(voucher_no="PI-2", item_row="r1", rate=0, taxable=869.57, vat=130.44),
				invoice_row(voucher_no="PI-3", item_row="r1", rate=0, taxable=1000, vat=73.3),
			]
		)
		self.assertEqual(
			sorted((v, line.rate, line.taxable_amount, line.vat_amount) for (v, *_k), line in lines.items()),
			[("PI-1", 15, 1000, 155), ("PI-2", 15, 869.57, 130.44), ("PI-3", 7.33, 1000, 73.3)],
		)

	def test_zero_rated_line_stays_zero_rated(self):
		make_purchase_invoice(rate=400, bill_no="SUP-ZERO-1", vat_rate=0)

		boxes, _data = self.summary()
		self.assertEqual(boxes["10"]["amount"], 400)
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))

	def test_bank_name_on_entries_without_a_party(self):
		set_cutoff(add_days(nowdate(), -400))
		bank = make_bank_vat_journal_entry(30)

		# an entry without a supplier is left out of the detail; the exceptions report names the bank
		_columns, lines = execute_detail(self.filters(voucher_type="Journal Entry"))
		self.assertEqual(lines, [])
		rows = list(self.exceptions().values())
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["party_name"], frappe.db.get_value("Account", bank, "account_name"))
		self.assertFalse(rows[0]["party"])
		self.assertFalse(rows[0]["tax_id"])

	def test_bank_name_from_the_bank_account(self):
		"""A row linked to a Bank Account shows the Bank's name, not Bank Account.account_name (the holder)."""
		set_cutoff(add_days(nowdate(), -400))
		bank_ledger = make_bank_ledger("_Test KSA Bank Ledger")
		if not frappe.db.exists("Bank", "_Test KSA Bank"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "_Test KSA Bank"}).insert()
		bank_account = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": COMPANY,
				"bank": "_Test KSA Bank",
				"is_company_account": 1,
				"company": COMPANY,
				"account": bank_ledger,
			}
		).insert()
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": COMPANY,
				"posting_date": nowdate(),
				"accounts": [
					{
						"account": INPUT_VAT,
						"debit_in_account_currency": 3.75,
						"cost_center": f"Main - {ABBR}",
					},
					{
						"account": bank_ledger,
						"bank_account": bank_account.name,
						"credit_in_account_currency": 3.75,
						"cost_center": f"Main - {ABBR}",
					},
				],
			}
		)
		je.insert()
		je.submit()

		self.assertEqual(
			[(row["voucher_no"], row["party_name"]) for row in self.exceptions().values()],
			[(je.name, "_Test KSA Bank")],
		)

	def test_reclassification_entries_are_left_out(self):
		"""A Journal Entry with output VAT and the entry that reverses it (no supplier or customer) both leave
		the return; so do a bank VAT entry and the unlinked entry that reverses it (Dr expense / Cr Input VAT)."""
		set_cutoff(add_days(nowdate(), -400))
		si = make_sales_invoice(rate=1000)
		before, _data = self.summary()
		make_vat_journal_entry(net=100)
		reclass(OUTPUT_VAT, f"Sales - {ABBR}", 15, debit_vat=True)
		make_bank_vat_journal_entry(30)
		reclass(INPUT_VAT, f"Cost of Goods Sold - {ABBR}", 30)

		boxes, _data = self.summary()
		for no in ("1", "6", "7", "12", "13"):
			self.assertEqual(boxes[no], before[no], no)
		self.assertEqual(boxes["7"]["vat_amount"], 0)
		rows = self.exceptions()
		self.assertNotIn(si.name, rows)
		self.assertEqual({row["status"] for row in rows.values()}, {"Excluded"})
		self.assertEqual(len(rows), 4)

	def test_vat_account_without_tax_rate(self):
		frappe.db.set_value("Account", OUTPUT_VAT, "tax_rate", 0)
		frappe.clear_cache()
		set_cutoff(add_days(nowdate(), 30))
		make_vat_journal_entry(net=100)
		boxes, _data = self.summary()
		self.assertEqual((boxes["1"]["amount"], boxes["1"]["vat_amount"]), (0, 15))
		self.assertEqual(boxes["3"]["amount"], 0)

	def test_opening_entries_are_not_reported(self):
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": COMPANY,
				"posting_date": nowdate(),
				"is_opening": "Yes",
				"accounts": [
					{
						"account": f"Debtors - {ABBR}",
						"party_type": "Customer",
						"party": CUSTOMER,
						"debit_in_account_currency": 15,
						"cost_center": f"Main - {ABBR}",
					},
					{
						"account": OUTPUT_VAT,
						"credit_in_account_currency": 15,
						"cost_center": f"Main - {ABBR}",
					},
				],
			}
		)
		je.insert()
		je.submit()

		boxes, _data = self.summary()
		self.assertEqual(boxes["1"]["vat_amount"], 0)

		_columns, lines = execute_detail(self.filters())
		self.assertEqual(lines, [])
		_columns, rows = execute_exceptions(self.filters(show_not_reported=1))
		self.assertEqual([(row["status"], row["vat_amount"]) for row in rows], [("Not reported", 15)])
		self.assertEqual(self.exceptions(), {})

	def test_cancelled_invoices_are_not_reported(self):
		make_sales_invoice(rate=1000).cancel()
		boxes, _data = self.summary()
		self.assertEqual((boxes["1"]["amount"], boxes["1"]["vat_amount"]), (0, 0))

	def test_settings_validation(self):
		settings = frappe.get_doc("KSA VAT Settings", COMPANY)
		settings.append("ksa_vat_accounts", {"account": OUTPUT_VAT, "vat_account_type": "Input VAT"})
		self.assertRaises(frappe.ValidationError, settings.save)

		settings.reload()
		settings.ksa_vat_accounts = [
			row for row in settings.ksa_vat_accounts if row.vat_account_type != "Input VAT"
		]
		self.assertRaises(frappe.ValidationError, settings.save)

		settings.reload()
		settings.append("ksa_vat_accounts", {"account": "Sales - _TC", "vat_account_type": "VAT Settlement"})
		self.assertRaises(frappe.ValidationError, settings.save)


def make_company():
	if frappe.db.exists("Company", COMPANY):
		return
	frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": COMPANY,
			"abbr": ABBR,
			"country": "Saudi Arabia",
			"default_currency": "SAR",
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
			"tax_id": "300000000000099",
		}
	).insert()


def make_vat_accounts():
	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": "Tax", "is_group": 1}, "name"
	) or frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Liability", "is_group": 1}, "name")
	for account_name, rate in (("Output VAT 15%", 15), ("Input VAT 15%", 15), ("VAT Payable", 0)):
		if frappe.db.exists("Account", f"{account_name} - {ABBR}"):
			continue
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent,
				"company": COMPANY,
				"account_type": "Tax",
				"tax_rate": rate,
			}
		).insert()


def make_settings():
	if frappe.db.exists("KSA VAT Settings", COMPANY):
		return
	frappe.get_doc(
		{
			"doctype": "KSA VAT Settings",
			"company": COMPANY,
			"ksa_vat_accounts": [
				{"account": OUTPUT_VAT, "vat_account_type": "Output VAT"},
				{"account": INPUT_VAT, "vat_account_type": "Input VAT"},
				{"account": VAT_PAYABLE, "vat_account_type": "VAT Settlement"},
			],
		}
	).insert()


def make_parties():
	for name in (CUSTOMER, EXPORT_CUSTOMER):
		if not frappe.db.exists("Customer", name):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"tax_id": "310000000000003",
				}
			).insert()
	if not frappe.db.exists("Address", {"address_title": EXPORT_CUSTOMER}):
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": EXPORT_CUSTOMER,
				"address_type": "Billing",
				"address_line1": "1 Export Street",
				"city": "Dubai",
				"country": "United Arab Emirates",
				"links": [{"link_doctype": "Customer", "link_name": EXPORT_CUSTOMER}],
			}
		).insert()
	if not frappe.db.exists("Supplier", SUPPLIER):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": SUPPLIER,
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
				"tax_id": "300000000000003",
			}
		).insert()


def make_item():
	if frappe.db.exists("Item", ITEM):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": ITEM,
			"item_name": ITEM,
			"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
			"is_stock_item": 0,
			"stock_uom": "Nos",
		}
	).insert()


def make_sales_invoice(rate, vat_rate=15, customer=CUSTOMER):
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": customer,
			"currency": "SAR",
			"posting_date": nowdate(),
			"set_posting_time": 1,
			"debit_to": f"Debtors - {ABBR}",
			"customer_address": frappe.db.get_value("Address", {"address_title": customer}, "name"),
			"items": [
				{
					"item_code": ITEM,
					"qty": 1,
					"rate": rate,
					"income_account": f"Sales - {ABBR}",
					"cost_center": f"Main - {ABBR}",
				}
			],
			"taxes": [
				{
					"charge_type": "On Net Total",
					"account_head": OUTPUT_VAT,
					"description": "VAT",
					"rate": vat_rate,
					"cost_center": f"Main - {ABBR}",
				}
			],
		}
	)
	si.insert()
	si.submit()
	return si


def make_purchase_invoice(
	rate,
	bill_no,
	vat_rate=15,
	actual_vat=None,
	supplier=SUPPLIER,
	verified=True,
	attach=True,
	posting_date=None,
):
	"""A complete purchase by default: bill_no, buyer details verified and a file attached. Turn an element
	off with bill_no=None, verified=False or attach=False; the supplier keeps its tax ID.
	actual_vat: VAT as an "Actual" amount (Item Wise Tax Detail then stores rate 0)."""
	tax = {
		"charge_type": "On Net Total",
		"category": "Total",
		"add_deduct_tax": "Add",
		"account_head": INPUT_VAT,
		"description": "VAT",
		"rate": vat_rate,
		"cost_center": f"Main - {ABBR}",
	}
	if actual_vat is not None:
		tax.update({"charge_type": "Actual", "rate": 0, "tax_amount": actual_vat})
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": COMPANY,
			"supplier": supplier,
			"currency": "SAR",
			"posting_date": posting_date or nowdate(),
			"set_posting_time": 1,
			"bill_no": bill_no,
			"bill_date": posting_date or nowdate(),
			"sijill_buyer_details_verified": 1 if verified else 0,
			"credit_to": f"Creditors - {ABBR}",
			"items": [
				{
					"item_code": ITEM,
					"qty": 1,
					"rate": rate,
					"expense_account": f"Cost of Goods Sold - {ABBR}",
					"cost_center": f"Main - {ABBR}",
				}
			],
			"taxes": [tax],
		}
	)
	pi.insert()
	pi.submit()
	if attach:
		attach_file(pi)
	return pi


def attach_file(doc):
	"""A private file attached to the voucher (the copy of the supplier invoice)."""
	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{doc.name}.txt",
			"content": f"copy of {doc.name}",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"is_private": 1,
		}
	).insert()


def make_supplier(name, tax_id="300000000000003"):
	if not frappe.db.exists("Supplier", name):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": name,
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
				"tax_id": tax_id,
			}
		).insert()
	return name


def make_purchase_return(pi, verified=True, attach=True, keep_bill_no=True):
	"""Full return (debit note) of a Purchase Invoice, complete by default; keeps the bill no of the original
	(keep_bill_no=False leaves it empty)."""
	ret = make_return_doc("Purchase Invoice", pi.name)
	ret.bill_no = pi.bill_no if keep_bill_no else None
	ret.sijill_buyer_details_verified = 1 if verified else 0
	ret.submit()
	if attach:
		attach_file(ret)
	return ret


def make_purchase_journal_entry(
	vat,
	bill_no,
	supplier=SUPPLIER,
	party_type="Supplier",
	verified=True,
	attach=True,
	cheque_no=None,
	posting_date=None,
	reduction=False,
):
	"""A purchase booked as a Journal Entry: Dr Input VAT and expense, Cr Creditors with a Supplier party row.
	Complete by default. Turn an element off with bill_no=None, verified=False or attach=False;
	party_type="Customer" books the credit to a Customer, party_type=None to a bank account (no party).
	reduction=True reverses every side (Cr Input VAT and expense, Dr Creditors): a purchase that reduces VAT."""
	net = flt(vat * 100 / 15, 2)
	expense_side, credit_side = ("credit", "debit") if reduction else ("debit", "credit")
	credit = {f"{credit_side}_in_account_currency": net + vat, "cost_center": f"Main - {ABBR}"}
	if party_type == "Supplier":
		credit.update({"account": f"Creditors - {ABBR}", "party_type": "Supplier", "party": supplier})
	elif party_type == "Customer":
		credit.update({"account": f"Debtors - {ABBR}", "party_type": "Customer", "party": CUSTOMER})
	else:
		credit["account"] = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0}, "name"
		)
	date = posting_date or nowdate()
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": date,
			"bill_no": bill_no,
			"bill_date": date if bill_no else None,
			"cheque_no": cheque_no,
			"cheque_date": date if cheque_no else None,
			"sijill_buyer_details_verified": 1 if verified else 0,
			"accounts": [
				{
					"account": f"Cost of Goods Sold - {ABBR}",
					f"{expense_side}_in_account_currency": net,
					"cost_center": f"Main - {ABBR}",
				},
				{
					"account": INPUT_VAT,
					f"{expense_side}_in_account_currency": vat,
					"cost_center": f"Main - {ABBR}",
				},
				credit,
			],
		}
	)
	je.insert()
	je.submit()
	if attach:
		attach_file(je)
	return je


def make_vat_journal_entry(net, is_opening="No", posting_date=None):
	vat = net * 15 / 100
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": posting_date or nowdate(),
			"is_opening": is_opening,
			"cheque_no": "JE-REF-1",
			"cheque_date": nowdate(),
			"accounts": [
				{
					"account": f"Debtors - {ABBR}",
					"party_type": "Customer",
					"party": CUSTOMER,
					"debit_in_account_currency": net + vat,
					"cost_center": f"Main - {ABBR}",
				},
				{
					"account": f"Sales - {ABBR}",
					"credit_in_account_currency": net,
					"cost_center": f"Main - {ABBR}",
				},
				{
					"account": OUTPUT_VAT,
					"credit_in_account_currency": vat,
					"cost_center": f"Main - {ABBR}",
				},
			],
		}
	)
	je.insert()
	je.submit()
	return je


def make_settlement_journal_entry():
	"""Closes the period: output VAT less input VAT into VAT Payable."""
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": nowdate(),
			"accounts": [
				{"account": OUTPUT_VAT, "debit_in_account_currency": 135, "cost_center": f"Main - {ABBR}"},
				{"account": INPUT_VAT, "credit_in_account_currency": 75, "cost_center": f"Main - {ABBR}"},
				{"account": VAT_PAYABLE, "credit_in_account_currency": 60, "cost_center": f"Main - {ABBR}"},
			],
		}
	)
	je.insert()
	je.submit()
	return je


def make_bank_vat_journal_entry(vat):
	"""VAT a bank charges on its fees: Dr Input VAT, Cr Bank, no party. Returns the bank account."""
	bank = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0}, "name"
	)
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": nowdate(),
			"accounts": [
				{"account": INPUT_VAT, "debit_in_account_currency": vat, "cost_center": f"Main - {ABBR}"},
				{"account": bank, "credit_in_account_currency": vat, "cost_center": f"Main - {ABBR}"},
			],
		}
	)
	je.insert()
	je.submit()
	return bank


def set_cutoff(date):
	"""KSA VAT Settings "Output VAT from Sales Invoices only, from date" of the test company; None: empty."""
	frappe.db.set_value("KSA VAT Settings", COMPANY, "output_vat_invoices_only_from", date)


def reclass(vat_account, other_account, amount, debit_vat=False, posting_date=None):
	"""Journal Entry without a party that moves `amount` between a VAT account and a revenue or expense account."""
	vat_side, other_side = ("debit", "credit") if debit_vat else ("credit", "debit")
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": posting_date or nowdate(),
			"accounts": [
				{
					"account": vat_account,
					f"{vat_side}_in_account_currency": amount,
					"cost_center": f"Main - {ABBR}",
				},
				{
					"account": other_account,
					f"{other_side}_in_account_currency": amount,
					"cost_center": f"Main - {ABBR}",
				},
			],
		}
	)
	je.insert()
	je.submit()
	return je


def invoice_row(item_row, rate, taxable, vat, voucher_no="PI-1"):
	"""One row as the invoice queries return it (one per invoice, item row and stored rate)."""
	return frappe._dict(
		voucher_no=voucher_no,
		item_row=item_row,
		rate=rate,
		taxable_amount=taxable,
		vat_amount=vat,
		vat_account=INPUT_VAT,
		is_adjustment=0,
		posting_date=nowdate(),
		party=SUPPLIER,
		party_name=SUPPLIER,
		bill_no=None,
		bill_date=None,
		party_country=None,
	)


def make_bank_ledger(account_name):
	"""A new Bank-type ledger account of the test company, used by no Bank Account yet."""
	if frappe.db.exists("Account", f"{account_name} - {ABBR}"):
		return f"{account_name} - {ABBR}"
	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": "Bank", "is_group": 1}, "name"
	) or frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Asset", "is_group": 1}, "name")
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent,
				"company": COMPANY,
				"account_type": "Bank",
			}
		)
		.insert()
		.name
	)
