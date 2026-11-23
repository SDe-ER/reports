# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import frappe
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import nowdate

from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	EXCLUDED,
	EXPORTS,
	STANDARD_RATED_PURCHASES,
	STANDARD_RATED_SALES,
	ZERO_RATED_SALES,
	execute,
)
from sijill.sijill.report.ksa_vat_return_detail.ksa_vat_return_detail import (
	execute as execute_detail,
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

		_columns, lines = execute_detail(self.filters(show_excluded=1))
		excluded = [line for line in lines if line["category"] == EXCLUDED]
		self.assertEqual({line["vat_account"] for line in excluded}, {OUTPUT_VAT, INPUT_VAT})
		self.assertTrue(all(line["remarks"] for line in excluded))

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

		_columns, lines = execute_detail(self.filters(show_excluded=1, voucher_type="Journal Entry"))
		self.assertEqual([(line["category"], line["vat_amount"]) for line in lines], [(EXCLUDED, -150)])

	def test_vat_charged_by_the_bank_is_reported(self):
		"""Input VAT a bank charges on its fees (Dr Input VAT, Cr Bank) is a purchase, not a settlement."""
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
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (200, 30))

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

	def test_zero_rated_line_stays_zero_rated(self):
		make_purchase_invoice(rate=400, bill_no="SUP-ZERO-1", vat_rate=0)

		boxes, _data = self.summary()
		self.assertEqual(boxes["10"]["amount"], 400)
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))

	def test_bank_name_on_entries_without_a_party(self):
		bank = make_bank_vat_journal_entry(30)

		_columns, lines = execute_detail(self.filters(voucher_type="Journal Entry"))
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]["party_name"], frappe.db.get_value("Account", bank, "account_name"))
		self.assertFalse(lines[0]["party"])
		self.assertFalse(lines[0]["tax_id"])

	def test_reclassification_entries_net_out(self):
		"""Owner 2026-11-23: VAT removed by a reclassification JE (Dr Output VAT / Cr Sales; Dr Bank Charges /
		Cr Input VAT) instead of cancelling the original entry. The return nets both to zero VAT."""
		make_vat_journal_entry(net=100)
		reclass(OUTPUT_VAT, f"Sales - {ABBR}", 15, debit_vat=True)
		make_bank_vat_journal_entry(30)
		reclass(
			INPUT_VAT,
			frappe.db.get_value(
				"Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name"
			),
			30,
		)

		boxes, _data = self.summary()
		self.assertEqual(boxes["1"]["vat_amount"], 0)
		self.assertEqual(boxes["1"]["amount"] + boxes["1"]["adjustment"], 0)
		self.assertEqual(boxes["7"]["vat_amount"], 0)
		self.assertEqual(boxes["7"]["amount"] + boxes["7"]["adjustment"], 0)
		self.assertEqual(boxes["13"]["vat_amount"], 0)

	def test_vat_account_without_tax_rate(self):
		frappe.db.set_value("Account", OUTPUT_VAT, "tax_rate", 0)
		frappe.clear_cache()
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

		_columns, lines = execute_detail(self.filters(show_excluded=1))
		self.assertEqual([(line["category"], line["vat_amount"]) for line in lines], [(EXCLUDED, 15)])

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


def make_purchase_invoice(rate, bill_no, vat_rate=15, actual_vat=None):
	"""actual_vat: VAT as an "Actual" amount (Item Wise Tax Detail then stores rate 0)."""
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
			"supplier": SUPPLIER,
			"currency": "SAR",
			"posting_date": nowdate(),
			"set_posting_time": 1,
			"bill_no": bill_no,
			"bill_date": nowdate(),
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
	return pi


def make_vat_journal_entry(net, is_opening="No"):
	vat = net * 15 / 100
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": nowdate(),
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


def reclass(vat_account, other_account, amount, debit_vat=False):
	"""Reclassification JE: moves `amount` between a VAT account and a revenue or expense account."""
	vat_side, other_side = ("debit", "credit") if debit_vat else ("credit", "debit")
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": nowdate(),
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
