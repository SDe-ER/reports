# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""Tests of the data rules (Task K) and the reclassification pairs (Task L) of the KSA VAT Return."""

import frappe
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import add_months, flt, nowdate

from sijill.sijill.report.ksa_vat_return.data_rules import (
	BUYER_FIELD,
	RECLASS_FIELD,
	RULES,
	get_marker,
)
from sijill.sijill.report.ksa_vat_return.ksa_vat_return import (
	PURCHASE_CATEGORIES,
	SALES_CATEGORIES,
	STANDARD_RATED_PURCHASES,
	STANDARD_RATED_SALES,
	execute,
)
from sijill.sijill.report.ksa_vat_return.test_ksa_vat_return import (
	ABBR,
	COMPANY,
	INPUT_VAT,
	OUTPUT_VAT,
	SUPPLIER,
	make_bank_vat_journal_entry,
	make_company,
	make_item,
	make_parties,
	make_purchase_invoice,
	make_purchase_journal_entry,
	make_purchase_return,
	make_sales_invoice,
	make_settings,
	make_settlement_journal_entry,
	make_supplier,
	make_vat_accounts,
	make_vat_journal_entry,
	reclass,
)
from sijill.sijill.report.ksa_vat_return_detail.ksa_vat_return_detail import (
	execute as execute_detail,
)
from sijill.sijill.report.vat_documents_requiring_completion.vat_documents_requiring_completion import (
	execute as execute_exceptions,
)

CUSTOMER_WITHOUT_ID = "_Test KSA VAT Customer Without ID"
OTHER_SUPPLIER = "_Test KSA VAT Other Supplier"
COGS = f"Cost of Goods Sold - {ABBR}"
SALES = f"Sales - {ABBR}"


class VATRulesTestBase(ERPNextTestSuite):
	def setUp(self):
		make_company()
		make_vat_accounts()
		make_settings()
		make_parties()
		make_item()
		# the duplicate rule is ours; ERPNext's own uniqueness check would stop the second invoice
		frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 0)

	def filters(self, date=None, **extra):
		date = date or nowdate()
		return {"company": COMPANY, "from_date": date, "to_date": date, **extra}

	def boxes(self, date=None):
		_columns, data = execute(self.filters(date))
		return {row["no"]: row for row in data if row["no"]}

	def detail(self, date=None, **extra):
		return execute_detail(self.filters(date, **extra))[1]

	def exceptions(self, date=None, **extra):
		"""voucher_no -> exception row (one row per voucher in these tests)."""
		_columns, rows = execute_exceptions(self.filters(date, **extra))
		return {row["voucher_no"]: row for row in rows}

	def codes(self, row):
		return row["failed_codes"].split("; ")

	def detail_vouchers(self, date=None):
		return {line["voucher_no"] for line in self.detail(date)}

	def make_customer_without_id(self):
		if not frappe.db.exists("Customer", CUSTOMER_WITHOUT_ID):
			frappe.get_doc(
				{"doctype": "Customer", "customer_name": CUSTOMER_WITHOUT_ID, "customer_type": "Company"}
			).insert()
		return CUSTOMER_WITHOUT_ID


class TestVATDataRules(VATRulesTestBase):
	def assert_purchase_excluded(self, voucher, code):
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))
		self.assertEqual((boxes["12"]["amount"], boxes["12"]["vat_amount"]), (0, 0))
		self.assertNotIn(voucher.name, self.detail_vouchers())
		row = self.exceptions()[voucher.name]
		self.assertEqual((row["status"], row["side"], row["failed_codes"]), ("Excluded", "Purchase", code))
		self.assertEqual(row["failed_rules_en"], RULES[code][0])
		self.assertEqual(row["failed_rules_ar"], RULES[code][1])

	# purchase invoices

	def test_complete_purchase_is_counted(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-OK-1")
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (500, 75))
		self.assertEqual((boxes["12"]["amount"], boxes["12"]["vat_amount"]), (500, 75))
		self.assertIn(pi.name, self.detail_vouchers())
		self.assertEqual(self.exceptions(), {})

	def test_bill_no_missing(self):
		self.assert_purchase_excluded(make_purchase_invoice(rate=500, bill_no=None), "BILL_NO_MISSING")

	def test_bill_no_blank_spaces_is_missing(self):
		self.assert_purchase_excluded(make_purchase_invoice(rate=500, bill_no="   "), "BILL_NO_MISSING")

	def test_bill_no_duplicate(self):
		first = make_purchase_invoice(rate=500, bill_no="K-DUP-1")
		second = make_purchase_invoice(rate=200, bill_no=" k-dup-1 ")
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))
		rows = self.exceptions()
		for pi in (first, second):
			self.assertEqual(
				(rows[pi.name]["status"], rows[pi.name]["failed_codes"]), ("Excluded", "BILL_NO_DUPLICATE")
			)
		self.assertEqual(self.detail(), [])

	def test_bill_no_duplicate_counts_all_dates(self):
		make_purchase_invoice(rate=500, bill_no="K-DUP-2", posting_date=add_months(nowdate(), -1))
		current = make_purchase_invoice(rate=200, bill_no="K-DUP-2")
		self.assertEqual(self.exceptions()[current.name]["failed_codes"], "BILL_NO_DUPLICATE")

	def test_same_bill_no_for_different_suppliers_passes(self):
		other = make_supplier(OTHER_SUPPLIER)
		make_purchase_invoice(rate=500, bill_no="K-SAME-1")
		make_purchase_invoice(rate=200, bill_no="K-SAME-1", supplier=other)
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (700, 105))
		self.assertEqual(self.exceptions(), {})

	def test_returns_are_not_duplicates(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-RET-1")
		make_purchase_return(pi)
		self.assertEqual(self.exceptions(), {})
		boxes = self.boxes()
		self.assertEqual(boxes["7"]["amount"] + boxes["7"]["adjustment"], 0)
		self.assertEqual(boxes["7"]["vat_amount"], 0)

	def test_supplier_name_missing(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-NAME-1")
		frappe.db.set_value("Purchase Invoice", pi.name, "supplier_name", "")
		self.assert_purchase_excluded(pi, "SUPPLIER_NAME_MISSING")

	def test_supplier_vat_invalid(self):
		"""No tax ID, 14 digits, 15 digits not starting with 3, 15 digits not ending in 3, a letter."""
		invoices = {}
		for index, tax_id in enumerate(
			("", "30000000000003", "400000000000003", "300000000000001", "30000000000000A")
		):
			supplier = make_supplier(f"_Test KSA VAT Bad Tax {index}", tax_id=tax_id)
			invoices[tax_id] = make_purchase_invoice(rate=100, bill_no=f"K-TAX-{index}", supplier=supplier)
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))
		rows = self.exceptions()
		for tax_id, pi in invoices.items():
			self.assertEqual(
				(rows[pi.name]["status"], rows[pi.name]["failed_codes"]),
				("Excluded", "SUPPLIER_VAT_INVALID"),
				tax_id,
			)
		self.assertEqual(self.detail(), [])

	def test_buyer_details_not_verified(self):
		self.assert_purchase_excluded(
			make_purchase_invoice(rate=500, bill_no="K-BUY-1", verified=False), "BUYER_DETAILS_NOT_VERIFIED"
		)

	def test_attachment_missing(self):
		self.assert_purchase_excluded(
			make_purchase_invoice(rate=500, bill_no="K-ATT-1", attach=False), "ATTACHMENT_MISSING"
		)

	def test_all_failed_rules_are_listed(self):
		pi = make_purchase_invoice(rate=500, bill_no=None, verified=False, attach=False)
		row = self.exceptions()[pi.name]
		self.assertEqual(
			self.codes(row), ["BILL_NO_MISSING", "BUYER_DETAILS_NOT_VERIFIED", "ATTACHMENT_MISSING"]
		)
		self.assertEqual(row["failed_rules_en"], "; ".join(RULES[code][0] for code in self.codes(row)))
		self.assertEqual(row["failed_rules_ar"], "; ".join(RULES[code][1] for code in self.codes(row)))

	def test_buyer_verification_can_be_set_after_submit(self):
		"""The reviewer confirms on the submitted invoice (allow_on_submit); it then enters the return."""
		pi = make_purchase_invoice(rate=500, bill_no="K-BUY-2", verified=False)
		self.assertIn(pi.name, self.exceptions())
		pi.db_set(BUYER_FIELD, 1)
		self.assertEqual(self.boxes()["7"]["amount"], 500)
		self.assertEqual(self.exceptions(), {})

	def test_excluded_reduction_is_flagged(self):
		"""Excluding a voucher that reduces input VAT increases the claim: it also gets REDUCTION_EXCLUDED."""
		je = reclass(INPUT_VAT, COGS, 30)
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertIn("REDUCTION_EXCLUDED", self.codes(row))
		self.assertIn("BILL_NO_MISSING", self.codes(row))
		self.assertEqual(row["vat_amount"], -30)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	# Journal Entries with input VAT

	def test_complete_journal_entry_purchase_is_counted(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-OK")
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (200, 30))
		line = next(line for line in self.detail() if line["voucher_no"] == je.name)
		self.assertEqual(
			(line["bill_no"], line["party_name"], line["tax_id"]),
			("K-JE-OK", SUPPLIER, "300000000000003"),
		)
		self.assertEqual(self.exceptions(), {})

	def test_journal_entry_bill_no_missing(self):
		self.assert_purchase_excluded(make_purchase_journal_entry(vat=30, bill_no=None), "BILL_NO_MISSING")

	def test_journal_entry_cheque_no_is_not_a_bill_no(self):
		je = make_purchase_journal_entry(vat=30, bill_no=None, cheque_no="CHQ-1")
		self.assert_purchase_excluded(je, "BILL_NO_MISSING")

	def test_journal_entry_without_a_party_is_excluded(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-NP", party_type=None)
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertEqual(self.codes(row), ["SUPPLIER_NAME_MISSING", "SUPPLIER_VAT_INVALID"])
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	def test_journal_entry_with_a_customer_party_is_excluded(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-CU", party_type="Customer")
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertIn("SUPPLIER_NAME_MISSING", self.codes(row))
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	def test_journal_entry_supplier_vat_invalid(self):
		supplier = make_supplier("_Test KSA VAT JE Bad Tax", tax_id="300000000000001")
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-TX", supplier=supplier)
		self.assert_purchase_excluded(je, "SUPPLIER_VAT_INVALID")

	def test_journal_entry_buyer_details_not_verified(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-BU", verified=False)
		self.assert_purchase_excluded(je, "BUYER_DETAILS_NOT_VERIFIED")

	def test_journal_entry_attachment_missing(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-AT", attach=False)
		self.assert_purchase_excluded(je, "ATTACHMENT_MISSING")

	def test_duplicate_across_invoice_and_journal_entry(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-X-1")
		je = make_purchase_journal_entry(vat=30, bill_no="k-x-1")
		rows = self.exceptions()
		for voucher in (pi, je):
			self.assertEqual(
				(rows[voucher.name]["status"], rows[voucher.name]["failed_codes"]),
				("Excluded", "BILL_NO_DUPLICATE"),
			)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	def test_same_bill_no_on_invoice_and_journal_entry_of_different_suppliers(self):
		other = make_supplier(OTHER_SUPPLIER)
		make_purchase_invoice(rate=500, bill_no="K-X-2")
		make_purchase_journal_entry(vat=30, bill_no="K-X-2", supplier=other)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 105)
		self.assertEqual(self.exceptions(), {})

	# sales warnings

	def test_sales_without_customer_vat_are_counted_and_warned(self):
		si = make_sales_invoice(rate=1000, customer=self.make_customer_without_id())
		boxes = self.boxes()
		self.assertEqual((boxes["1"]["amount"], boxes["1"]["vat_amount"]), (1000, 150))

		row = self.exceptions()[si.name]
		self.assertEqual(
			(row["status"], row["side"], row["failed_codes"]),
			("Included (warning)", "Sales", "CUSTOMER_ID_MISSING"),
		)
		line = next(line for line in self.detail() if line["voucher_no"] == si.name)
		self.assertEqual(line["tax_id"], get_marker())
		self.assertEqual(line["party_name"], CUSTOMER_WITHOUT_ID)

	def test_sales_with_invalid_customer_vat_are_counted_and_warned(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test KSA VAT Customer Bad Tax",
				"customer_type": "Company",
				"tax_id": "123",
			}
		).insert()
		si = make_sales_invoice(rate=1000, customer=customer.name)
		self.assertEqual(self.boxes()["1"]["amount"], 1000)
		row = self.exceptions()[si.name]
		self.assertEqual(row["status"], "Included (warning)")
		self.assertEqual(self.codes(row), ["CUSTOMER_ID_MISSING", "CUSTOMER_VAT_INVALID"])
		line = next(line for line in self.detail() if line["voucher_no"] == si.name)
		self.assertEqual(line["tax_id"], "123")

	def test_complete_sales_have_no_warning(self):
		make_sales_invoice(rate=1000)
		make_vat_journal_entry(net=100)
		self.assertEqual(self.exceptions(), {})

	# detail and totals

	def make_mixed_scenario(self):
		si = make_sales_invoice(rate=1000)
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.items[0].qty = -1
		credit_note.items[0].rate = 200
		credit_note.submit()
		make_sales_invoice(rate=400, customer=self.make_customer_without_id())
		make_sales_invoice(rate=300, vat_rate=0)
		make_vat_journal_entry(net=100)
		make_purchase_invoice(rate=500, bill_no="K-MIX-1")
		make_purchase_return(make_purchase_invoice(rate=300, bill_no="K-MIX-2"))
		make_purchase_invoice(rate=111, bill_no=None)
		make_purchase_invoice(rate=222, bill_no="K-MIX-3", attach=False)
		make_purchase_journal_entry(vat=30, bill_no="K-MIX-JE")
		make_purchase_journal_entry(vat=45, bill_no=None, party_type=None)
		make_bank_vat_journal_entry(15)
		make_settlement_journal_entry()

	def test_detail_has_no_empty_mandatory_cell(self):
		self.make_mixed_scenario()
		lines = self.detail()
		self.assertTrue(lines)
		for line in lines:
			for field in ("voucher_no", "bill_no", "party_name", "tax_id"):
				self.assertTrue(line[field], f"{field} is empty on {line['voucher_no']}")

	def test_return_totals_equal_detail_sums(self):
		self.make_mixed_scenario()
		boxes = self.boxes()
		lines = self.detail()

		def total(categories, adjustment=None):
			rows = [
				line
				for line in lines
				if line["category"] in categories
				and (adjustment is None or bool(line["is_adjustment"]) == adjustment)
			]
			return (
				flt(sum(line["taxable_amount"] for line in rows), 2),
				flt(sum(line["vat_amount"] for line in rows), 2),
			)

		for no, categories in (
			("1", (STANDARD_RATED_SALES,)),
			("6", SALES_CATEGORIES),
			("7", (STANDARD_RATED_PURCHASES,)),
			("12", PURCHASE_CATEGORIES),
		):
			self.assertEqual(boxes[no]["amount"], total(categories, adjustment=False)[0], no)
			self.assertEqual(boxes[no]["adjustment"], total(categories, adjustment=True)[0], no)
			self.assertEqual(boxes[no]["vat_amount"], total(categories)[1], no)
		self.assertEqual(
			boxes["13"]["vat_amount"], flt(total(SALES_CATEGORIES)[1] - total(PURCHASE_CATEGORIES)[1], 2)
		)
		# the scenario really has excluded and warned vouchers
		statuses = {row["status"] for row in self.exceptions().values()}
		self.assertEqual(statuses, {"Excluded", "Included (warning)"})

	# the exceptions report

	def test_exceptions_report_filters(self):
		make_sales_invoice(rate=1000, customer=self.make_customer_without_id())
		make_purchase_invoice(rate=500, bill_no=None)
		make_settlement_journal_entry()

		rows = self.exceptions()
		self.assertEqual({row["side"] for row in rows.values()}, {"Sales", "Purchase"})
		self.assertEqual({row["status"] for row in rows.values()}, {"Excluded", "Included (warning)"})

		self.assertEqual({row["side"] for row in self.exceptions(side="Sales").values()}, {"Sales"})
		self.assertEqual({row["side"] for row in self.exceptions(side="Purchase").values()}, {"Purchase"})

		everything = self.exceptions(show_not_reported=1)
		not_reported = [row for row in everything.values() if row["status"] == "Not reported"]
		self.assertEqual(len(not_reported), 2)
		self.assertEqual({row["failed_codes"] for row in not_reported}, {"NOT_A_TAXABLE_TRANSACTION"})
		self.assertEqual(
			{row["side"] for row in self.exceptions(side="Sales", show_not_reported=1).values()}, {"Sales"}
		)

	def test_exceptions_report_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts User")
		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, execute_exceptions, self.filters())

	def test_custom_fields_exist(self):
		expected = {
			"Purchase Invoice-sijill_buyer_details_verified": ("Check", 1),
			"Journal Entry-sijill_buyer_details_verified": ("Check", 1),
			"Journal Entry-sijill_reclassification_of": ("Link", 0),
		}
		for name, (fieldtype, allow_on_submit) in expected.items():
			self.assertTrue(frappe.db.exists("Custom Field", name), name)
			field = frappe.db.get_value(
				"Custom Field", name, ["fieldtype", "allow_on_submit", "no_copy", "module"], as_dict=True
			)
			self.assertEqual((field.fieldtype, field.allow_on_submit), (fieldtype, allow_on_submit), name)
			self.assertEqual((field.no_copy, field.module), (1, "Sijill"), name)
		self.assertEqual(
			frappe.db.get_value("Custom Field", "Journal Entry-sijill_reclassification_of", "options"),
			"Journal Entry",
		)
		self.assertTrue(frappe.get_meta("Journal Entry").has_field(RECLASS_FIELD))
		self.assertTrue(frappe.get_meta("Purchase Invoice").has_field(BUYER_FIELD))


class TestVATReclassificationPairs(VATRulesTestBase):
	"""Task L: a Journal Entry that fully reverses the VAT of another one leaves the return."""

	def assert_pair(self, rows, first, second):
		"""Both vouchers are listed as Reclassified and name each other."""
		for voucher, partner in ((first, second), (second, first)):
			self.assertEqual(
				(rows[voucher.name]["status"], rows[voucher.name]["failed_codes"]),
				("Reclassified", "VAT_RECLASSIFIED"),
			)
			self.assertEqual(rows[voucher.name]["reclass_pair"], partner.name)

	def test_output_pair_leaves_amount_adjustment_and_detail(self):
		original = make_vat_journal_entry(net=100)
		pair = reclass(OUTPUT_VAT, SALES, 15, debit_vat=True, link=original.name)

		boxes = self.boxes()
		self.assertEqual(
			(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (0, 0, 0)
		)
		self.assertEqual((boxes["6"]["amount"], boxes["6"]["adjustment"]), (0, 0))
		self.assertEqual(self.detail(), [])
		rows = self.exceptions()
		self.assert_pair(rows, original, pair)
		self.assertEqual({row["side"] for row in rows.values()}, {"Sales"})

	def test_output_pair_in_different_periods(self):
		earlier = add_months(nowdate(), -1)
		original = make_vat_journal_entry(net=100, posting_date=earlier)
		pair = reclass(OUTPUT_VAT, SALES, 15, debit_vat=True, link=original.name)

		for date, voucher, partner in ((earlier, original, pair), (nowdate(), pair, original)):
			boxes = self.boxes(date)
			self.assertEqual(
				(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (0, 0, 0), date
			)
			self.assertEqual(self.detail(date), [], date)
			rows = self.exceptions(date)
			self.assertEqual(list(rows), [voucher.name], date)
			self.assertEqual(
				(rows[voucher.name]["status"], rows[voucher.name]["failed_codes"]),
				("Reclassified", "VAT_RECLASSIFIED"),
			)
			self.assertEqual(rows[voucher.name]["reclass_pair"], partner.name)

	def test_input_pair_leaves_amount_adjustment_and_detail(self):
		original = make_purchase_journal_entry(vat=30, bill_no="L-IN-1")
		pair = reclass(INPUT_VAT, COGS, 30, link=original.name)

		boxes = self.boxes()
		self.assertEqual(
			(boxes["7"]["amount"], boxes["7"]["adjustment"], boxes["7"]["vat_amount"]), (0, 0, 0)
		)
		self.assertEqual((boxes["12"]["amount"], boxes["12"]["adjustment"]), (0, 0))
		self.assertEqual(self.detail(), [])
		rows = self.exceptions()
		self.assert_pair(rows, original, pair)
		self.assertEqual({row["side"] for row in rows.values()}, {"Purchase"})

	def test_input_pair_in_a_later_period(self):
		earlier = add_months(nowdate(), -1)
		original = make_purchase_journal_entry(vat=30, bill_no="L-IN-2", posting_date=earlier)
		pair = reclass(INPUT_VAT, COGS, 30, link=original.name)

		self.assertEqual(self.boxes(earlier)["7"]["vat_amount"], 0)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)
		self.assertEqual(self.detail(earlier) + self.detail(), [])
		self.assertEqual(self.exceptions(earlier)[original.name]["reclass_pair"], pair.name)
		self.assertEqual(self.exceptions()[pair.name]["reclass_pair"], original.name)

	def test_pair_of_an_incomplete_original_is_reclassified_not_excluded(self):
		"""Pair lines do not go through the data rules."""
		original = make_purchase_journal_entry(vat=30, bill_no=None, verified=False, attach=False)
		pair = reclass(INPUT_VAT, COGS, 30, link=original.name)
		self.assert_pair(self.exceptions(), original, pair)

	def test_credit_note_still_shows_in_adjustment(self):
		si = make_sales_invoice(rate=1000)
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.items[0].qty = -1
		credit_note.items[0].rate = 200
		credit_note.submit()
		original = make_vat_journal_entry(net=100)
		reclass(OUTPUT_VAT, SALES, 15, debit_vat=True, link=original.name)

		boxes = self.boxes()
		self.assertEqual(
			(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (1000, -200, 120)
		)
		self.assertEqual({line["voucher_type"] for line in self.detail()}, {"Sales Invoice"})
		self.assertEqual({row["status"] for row in self.exceptions().values()}, {"Reclassified"})

	def test_partial_reclassification_is_kept_and_flagged(self):
		original = make_vat_journal_entry(net=100)
		partial = reclass(OUTPUT_VAT, SALES, 5, debit_vat=True, link=original.name)

		boxes = self.boxes()
		self.assertEqual(boxes["1"]["amount"], 100)
		self.assertAlmostEqual(boxes["1"]["adjustment"], -33.33, places=2)
		self.assertEqual(boxes["1"]["vat_amount"], 10)
		self.assertEqual(self.detail_vouchers(), {original.name, partial.name})
		rows = self.exceptions()
		for voucher in (original, partial):
			self.assertEqual(rows[voucher.name]["status"], "Included (warning)")
			self.assertIn("RECLASS_PARTIAL", self.codes(rows[voucher.name]))
			self.assertFalse(rows[voucher.name]["reclass_pair"])

	def test_partial_input_reclassification_is_flagged_and_checked_by_the_rules(self):
		original = make_purchase_journal_entry(vat=30, bill_no="L-PART-1")
		partial = reclass(INPUT_VAT, COGS, 10, link=original.name)

		rows = self.exceptions()
		self.assertIn(original.name, self.detail_vouchers())
		self.assertEqual(rows[original.name]["failed_codes"], "RECLASS_PARTIAL")
		self.assertEqual(rows[original.name]["status"], "Included (warning)")
		self.assertEqual(rows[partial.name]["status"], "Excluded")
		self.assertIn("RECLASS_PARTIAL", self.codes(rows[partial.name]))
		self.assertIn("REDUCTION_EXCLUDED", self.codes(rows[partial.name]))
		self.assertEqual(self.boxes()["7"]["vat_amount"], 30)

	def test_cancelled_reclassification_is_not_a_pair(self):
		original = make_vat_journal_entry(net=100)
		pair = reclass(OUTPUT_VAT, SALES, 15, debit_vat=True, link=original.name)
		pair.cancel()
		self.assertEqual(self.boxes()["1"]["vat_amount"], 15)
		self.assertEqual(self.exceptions(), {})

	def test_return_totals_equal_detail_sums_with_pairs(self):
		original = make_vat_journal_entry(net=100)
		reclass(OUTPUT_VAT, SALES, 15, debit_vat=True, link=original.name)
		make_sales_invoice(rate=1000)
		make_purchase_invoice(rate=500, bill_no="L-TOT-1")
		boxes = self.boxes()
		lines = self.detail()
		sales_vat = flt(sum(line["vat_amount"] for line in lines if line["category"] in SALES_CATEGORIES), 2)
		purchase_vat = flt(
			sum(line["vat_amount"] for line in lines if line["category"] in PURCHASE_CATEGORIES), 2
		)
		self.assertEqual(boxes["1"]["vat_amount"], sales_vat)
		self.assertEqual(boxes["7"]["vat_amount"], purchase_vat)
		self.assertEqual(boxes["13"]["vat_amount"], 75)
