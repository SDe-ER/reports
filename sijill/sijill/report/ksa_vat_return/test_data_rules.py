# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

"""Tests of the data rules of the KSA VAT Return: the return is built from invoices (Owner rule 2026-11-24)."""

import frappe
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import add_days, flt, getdate, nowdate

from sijill.sijill.doctype.ksa_vat_settings.ksa_vat_settings import get_rules_from_date
from sijill.sijill.report.ksa_vat_return.data_rules import BUYER_FIELD, RULES, get_marker
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
	set_cutoff,
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
MANDATORY = ("voucher_no", "bill_no", "party_name", "tax_id")


class VATRulesTestBase(ERPNextTestSuite):
	def setUp(self):
		make_company()
		make_vat_accounts()
		make_settings()
		make_parties()
		make_item()
		# the rules apply to every date of these tests; an empty cutoff would switch them off
		set_cutoff(add_days(nowdate(), -400))
		# the duplicate rule is ours; ERPNext's own uniqueness check would stop the second invoice
		frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 0)

	def filters(self, date=None, **extra):
		date = date or nowdate()
		return {"company": COMPANY, "from_date": date, "to_date": date, **extra}

	def boxes(self, date=None, **extra):
		_columns, data = execute(self.filters(date, **extra))
		return {row["no"]: row for row in data if row["no"]}

	def detail(self, date=None, **extra):
		return execute_detail(self.filters(date, **extra))[1]

	def exceptions(self, date=None, **extra):
		"""voucher_no -> exception row (one row per voucher in these tests)."""
		_columns, rows = execute_exceptions(self.filters(date, **extra))
		return {row["voucher_no"]: row for row in rows}

	def codes(self, row):
		return row["failed_codes"].split("; ")

	def detail_vouchers(self, date=None, **extra):
		return {line["voucher_no"] for line in self.detail(date, **extra)}

	def make_customer_without_id(self):
		if not frappe.db.exists("Customer", CUSTOMER_WITHOUT_ID):
			frappe.get_doc(
				{"doctype": "Customer", "customer_name": CUSTOMER_WITHOUT_ID, "customer_type": "Company"}
			).insert()
		return CUSTOMER_WITHOUT_ID

	def assert_purchase_excluded(self, voucher, code):
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (0, 0))
		self.assertEqual((boxes["12"]["amount"], boxes["12"]["vat_amount"]), (0, 0))
		self.assertNotIn(voucher.name, self.detail_vouchers())
		row = self.exceptions()[voucher.name]
		self.assertEqual((row["status"], row["side"], row["failed_codes"]), ("Excluded", "Purchase", code))
		self.assertEqual(row["failed_rules_en"], RULES[code][0])
		self.assertEqual(row["failed_rules_ar"], RULES[code][1])


class TestVATPurchaseRules(VATRulesTestBase):
	"""Rules a to d exclude a purchase; a missing attachment is only a warning."""

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
		make_purchase_invoice(rate=500, bill_no="K-DUP-2", posting_date=add_days(nowdate(), -40))
		current = make_purchase_invoice(rate=200, bill_no="K-DUP-2")
		self.assertEqual(self.exceptions()[current.name]["failed_codes"], "BILL_NO_DUPLICATE")

	def test_same_bill_no_for_different_suppliers_passes(self):
		other = make_supplier(OTHER_SUPPLIER)
		make_purchase_invoice(rate=500, bill_no="K-SAME-1")
		make_purchase_invoice(rate=200, bill_no="K-SAME-1", supplier=other)
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (700, 105))
		self.assertEqual(self.exceptions(), {})

	def test_purchase_return_is_counted_in_adjustment_and_is_not_a_duplicate(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-RET-1")
		make_purchase_return(pi)
		self.assertEqual(self.exceptions(), {})
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["adjustment"]), (500, -500))
		self.assertEqual(boxes["7"]["vat_amount"], 0)

	def test_reversing_journal_entry_does_not_make_the_invoice_a_duplicate(self):
		"""A Journal Entry counts for the duplicate check only when it debits input VAT."""
		pi = make_purchase_invoice(rate=500, bill_no="K-REV-1")
		je = make_purchase_journal_entry(vat=30, bill_no="K-REV-1", reduction=True)
		self.assertEqual(self.exceptions(), {})
		self.assertEqual({pi.name, je.name}, self.detail_vouchers())
		self.assertEqual(self.boxes()["7"]["vat_amount"], 45)

	def test_return_passes_the_buyer_check_of_the_original(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-RET-2")
		ret = make_purchase_return(pi, verified=False)
		self.assertEqual(ret.get(BUYER_FIELD), 0)
		self.assertEqual(self.exceptions(), {})
		self.assertIn(ret.name, self.detail_vouchers())

	def test_return_of_an_unverified_original_is_excluded_too(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-RET-3", verified=False)
		ret = make_purchase_return(pi, verified=False)
		rows = self.exceptions()
		for voucher in (pi, ret):
			self.assertEqual(rows[voucher.name]["failed_codes"], "BUYER_DETAILS_NOT_VERIFIED")

	def test_return_without_a_bill_no_uses_the_one_of_the_original(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-RET-4")
		ret = make_purchase_return(pi, keep_bill_no=False)
		self.assertEqual(self.exceptions(), {})
		line = next(line for line in self.detail() if line["voucher_no"] == ret.name)
		self.assertEqual(line["bill_no"], "K-RET-4")

	def test_bill_no_duplicate_ignores_case_and_inner_spaces(self):
		first = make_purchase_invoice(rate=500, bill_no="INV 55")
		second = make_purchase_invoice(rate=200, bill_no="inv55")
		rows = self.exceptions()
		for pi in (first, second):
			self.assertEqual(
				(rows[pi.name]["status"], rows[pi.name]["failed_codes"]), ("Excluded", "BILL_NO_DUPLICATE")
			)

	def test_placeholder_bill_numbers_are_missing(self):
		for index, value in enumerate(
			("0", "-", "--", ".", "N/A", "NA", "none", "لا يوجد", "بدون", "", "   ")
		):
			with self.subTest(value=value):
				pi = make_purchase_invoice(rate=100, bill_no=value)
				row = self.exceptions()[pi.name]
				self.assertEqual((row["status"], row["failed_codes"]), ("Excluded", "BILL_NO_MISSING"), index)

	def test_bill_no_equal_to_the_invoice_name_is_missing(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-OWN-1")
		frappe.db.set_value("Purchase Invoice", pi.name, "bill_no", pi.name)
		self.assert_purchase_excluded(pi, "BILL_NO_MISSING")

	def test_placeholders_are_not_duplicates_of_each_other(self):
		first = make_purchase_invoice(rate=500, bill_no="-")
		second = make_purchase_invoice(rate=200, bill_no="-")
		rows = self.exceptions()
		for pi in (first, second):
			self.assertEqual(rows[pi.name]["failed_codes"], "BILL_NO_MISSING")

	def test_supplier_missing_on_invoice(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-NAME-1")
		frappe.db.set_value("Purchase Invoice", pi.name, "supplier_name", "")
		self.assert_purchase_excluded(pi, "SUPPLIER_MISSING")

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

	def test_buyer_verification_can_be_set_after_submit(self):
		"""The reviewer confirms on the submitted invoice (allow_on_submit); it then enters the return."""
		pi = make_purchase_invoice(rate=500, bill_no="K-BUY-2", verified=False)
		self.assertIn(pi.name, self.exceptions())
		pi.db_set(BUYER_FIELD, 1)
		self.assertEqual(self.boxes()["7"]["amount"], 500)
		self.assertEqual(self.exceptions(), {})

	def test_attachment_missing_is_only_a_warning(self):
		pi = make_purchase_invoice(rate=500, bill_no="K-ATT-1", attach=False)
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (500, 75))
		self.assertIn(pi.name, self.detail_vouchers())
		row = self.exceptions()[pi.name]
		self.assertEqual(
			(row["status"], row["side"], row["failed_codes"]),
			("Included (warning)", "Purchase", "ATTACHMENT_MISSING"),
		)

	def test_attachment_is_listed_with_the_failed_rules_of_an_excluded_voucher(self):
		pi = make_purchase_invoice(rate=500, bill_no=None, verified=False, attach=False)
		row = self.exceptions()[pi.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertEqual(
			self.codes(row), ["BILL_NO_MISSING", "BUYER_DETAILS_NOT_VERIFIED", "ATTACHMENT_MISSING"]
		)
		self.assertEqual(row["failed_rules_en"], "; ".join(RULES[code][0] for code in self.codes(row)))
		self.assertEqual(row["failed_rules_ar"], "; ".join(RULES[code][1] for code in self.codes(row)))

	def test_excluded_reduction_is_flagged_and_not_in_the_return(self):
		"""Excluding a voucher that reduces input VAT increases the claim: it also gets REDUCTION_EXCLUDED."""
		make_purchase_invoice(rate=500, bill_no="K-RED-0")
		je = reclass(INPUT_VAT, COGS, 30)
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertIn("BILL_NO_MISSING", self.codes(row))
		self.assertEqual(self.codes(row)[-1], "REDUCTION_EXCLUDED")
		self.assertEqual(row["vat_amount"], -30)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 75)
		self.assertNotIn(je.name, self.detail_vouchers())

	def test_qualifying_purchase_journal_entry_reduction_is_an_adjustment(self):
		make_purchase_invoice(rate=500, bill_no="K-RED-1")
		je = make_purchase_journal_entry(vat=30, bill_no="K-RED-JE", reduction=True)
		boxes = self.boxes()
		self.assertEqual(
			(boxes["7"]["amount"], boxes["7"]["adjustment"], boxes["7"]["vat_amount"]), (500, -200, 45)
		)
		self.assertIn(je.name, self.detail_vouchers())
		self.assertEqual(self.exceptions(), {})

	def test_incomplete_purchase_journal_entry_reduction_is_excluded(self):
		je = make_purchase_journal_entry(vat=30, bill_no=None, reduction=True)
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertEqual(self.codes(row), ["BILL_NO_MISSING", "REDUCTION_EXCLUDED"])
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

	def test_journal_entry_without_a_supplier_is_excluded(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-NP", party_type=None)
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertEqual(self.codes(row), ["SUPPLIER_MISSING", "SUPPLIER_VAT_INVALID"])
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	def test_journal_entry_with_a_customer_party_is_excluded(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-CU", party_type="Customer")
		row = self.exceptions()[je.name]
		self.assertEqual(row["status"], "Excluded")
		self.assertIn("SUPPLIER_MISSING", self.codes(row))
		self.assertEqual(self.boxes()["7"]["vat_amount"], 0)

	def test_journal_entry_supplier_vat_invalid(self):
		supplier = make_supplier("_Test KSA VAT JE Bad Tax", tax_id="300000000000001")
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-TX", supplier=supplier)
		self.assert_purchase_excluded(je, "SUPPLIER_VAT_INVALID")

	def test_journal_entry_buyer_details_not_verified(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-BU", verified=False)
		self.assert_purchase_excluded(je, "BUYER_DETAILS_NOT_VERIFIED")

	def test_journal_entry_attachment_missing_is_only_a_warning(self):
		je = make_purchase_journal_entry(vat=30, bill_no="K-JE-AT", attach=False)
		self.assertEqual(self.boxes()["7"]["vat_amount"], 30)
		row = self.exceptions()[je.name]
		self.assertEqual((row["status"], row["failed_codes"]), ("Included (warning)", "ATTACHMENT_MISSING"))

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


class TestVATSalesRules(VATRulesTestBase):
	"""Output VAT comes from Sales Invoices only, from the cutoff date on."""

	def test_output_vat_journal_entry_after_the_cutoff_is_ignored_and_listed(self):
		set_cutoff(add_days(nowdate(), -1))
		make_sales_invoice(rate=1000)
		before = self.boxes()
		je = make_vat_journal_entry(net=100)

		boxes = self.boxes()
		for no in ("1", "6", "13"):
			self.assertEqual(boxes[no], before[no], no)
		self.assertNotIn(je.name, self.detail_vouchers())
		row = self.exceptions()[je.name]
		self.assertEqual(
			(row["status"], row["side"], row["failed_codes"], row["vat_amount"]),
			("Excluded", "Sales", "OUTPUT_VAT_BY_JOURNAL_ENTRY", 15),
		)
		self.assertEqual(row["failed_rules_en"], RULES["OUTPUT_VAT_BY_JOURNAL_ENTRY"][0])

	def test_output_vat_journal_entry_before_the_cutoff_is_counted(self):
		set_cutoff(add_days(nowdate(), 1))
		je = make_vat_journal_entry(net=100)
		boxes = self.boxes()
		self.assertEqual(
			(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (100, 0, 15)
		)
		self.assertIn(je.name, self.detail_vouchers())
		self.assertEqual(self.exceptions(), {})

	def test_cutoff_on_the_posting_date_applies_the_rules(self):
		set_cutoff(nowdate())
		make_vat_journal_entry(net=100)
		self.assertEqual(self.boxes()["1"]["vat_amount"], 0)

	def test_empty_cutoff_switches_the_rules_off(self):
		"""Empty: the earlier behaviour. Nothing is left out; gaps are only listed as a warning."""
		set_cutoff(None)
		self.assertIsNone(get_rules_from_date(COMPANY))
		pi = make_purchase_invoice(rate=500, bill_no=None, verified=False)
		je = make_vat_journal_entry(net=100)
		reversal = reclass(OUTPUT_VAT, SALES, 15, debit_vat=True)

		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (500, 75))
		self.assertEqual((boxes["1"]["amount"], boxes["1"]["vat_amount"]), (100, 0))
		self.assertEqual(boxes["1"]["adjustment"], -100)
		self.assertTrue({pi.name, je.name, reversal.name} <= self.detail_vouchers())
		rows = self.exceptions()
		self.assertEqual(rows[pi.name]["status"], "Included (warning)")
		self.assertEqual(self.codes(rows[pi.name])[:2], ["BILL_NO_MISSING", "BUYER_DETAILS_NOT_VERIFIED"])
		self.assertEqual(rows[reversal.name]["status"], "Included (warning)")
		self.assertNotIn("Excluded", {row["status"] for row in rows.values()})

	def test_cutoff_setting_is_read(self):
		set_cutoff(add_days(nowdate(), 5))
		self.assertEqual(get_rules_from_date(COMPANY), getdate(add_days(nowdate(), 5)))

	def test_journal_entry_and_its_reclassification_both_leave_the_return(self):
		set_cutoff(add_days(nowdate(), -1))
		make_sales_invoice(rate=1000)
		before = self.boxes()
		original = make_vat_journal_entry(net=100)
		reversal = reclass(OUTPUT_VAT, SALES, 15, debit_vat=True)

		boxes = self.boxes()
		for no in ("1", "6", "13"):
			self.assertEqual(boxes[no], before[no], no)
		self.assertTrue({original.name, reversal.name}.isdisjoint(self.detail_vouchers()))
		rows = self.exceptions()
		self.assertEqual(
			(rows[original.name]["status"], rows[original.name]["failed_codes"]),
			("Excluded", "OUTPUT_VAT_BY_JOURNAL_ENTRY"),
		)
		# a reversal reduces output VAT: excluding it lowers the VAT due, so it is flagged
		self.assertEqual(
			(rows[reversal.name]["status"], self.codes(rows[reversal.name])),
			("Excluded", ["OUTPUT_VAT_BY_JOURNAL_ENTRY", "OUTPUT_REDUCTION_EXCLUDED"]),
		)

	def test_credit_note_shows_in_adjustment(self):
		si = make_sales_invoice(rate=1000)
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.items[0].qty = -1
		credit_note.items[0].rate = 200
		credit_note.submit()
		boxes = self.boxes()
		self.assertEqual(
			(boxes["1"]["amount"], boxes["1"]["adjustment"], boxes["1"]["vat_amount"]), (1000, -200, 120)
		)
		self.assertEqual(self.exceptions(), {})

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

	def test_complete_sales_invoice_has_no_warning(self):
		make_sales_invoice(rate=1000)
		self.assertEqual(self.exceptions(), {})


class TestVATBeforeTheCutoff(VATRulesTestBase):
	"""Lines before the cutoff keep the earlier behaviour: nothing is left out, gaps are only warned about."""

	def test_incomplete_purchases_before_the_cutoff_are_counted_with_a_warning(self):
		set_cutoff(add_days(nowdate(), 1))
		pi = make_purchase_invoice(rate=500, bill_no=None, verified=False, attach=False)
		je = make_purchase_journal_entry(vat=30, bill_no=None, party_type=None)

		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (700, 105))
		rows = self.exceptions()
		self.assertEqual(
			(rows[pi.name]["status"], self.codes(rows[pi.name])),
			("Included (warning)", ["BILL_NO_MISSING", "BUYER_DETAILS_NOT_VERIFIED", "ATTACHMENT_MISSING"]),
		)
		self.assertEqual(rows[je.name]["status"], "Included (warning)")
		self.assertIn("SUPPLIER_MISSING", self.codes(rows[je.name]))
		lines = {line["voucher_no"]: line for line in self.detail()}
		self.assertEqual(set(lines), {pi.name, je.name})
		self.assertEqual(lines[pi.name]["bill_no"], get_marker())
		self.assertEqual(lines[je.name]["party_name"], get_marker())
		self.assertEqual(lines[je.name]["tax_id"], get_marker())
		for line in lines.values():
			for field in MANDATORY:
				self.assertTrue(line[field], field)

	def test_bank_charge_before_the_cutoff_is_counted_with_the_bank_name(self):
		set_cutoff(add_days(nowdate(), 1))
		bank = make_bank_vat_journal_entry(30)
		boxes = self.boxes()
		self.assertEqual((boxes["7"]["amount"], boxes["7"]["vat_amount"]), (200, 30))
		lines = self.detail()
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]["party_name"], frappe.db.get_value("Account", bank, "account_name"))
		self.assertEqual(lines[0]["tax_id"], get_marker())
		for field in MANDATORY:
			self.assertTrue(lines[0][field], field)

	def test_journal_entry_shows_its_cheque_no_before_the_cutoff(self):
		set_cutoff(add_days(nowdate(), 1))
		je = make_purchase_journal_entry(vat=30, bill_no=None, cheque_no="CHQ-9")
		line = next(line for line in self.detail() if line["voucher_no"] == je.name)
		self.assertEqual(line["bill_no"], "CHQ-9")
		self.assertEqual(self.exceptions()[je.name]["status"], "Included (warning)")

	def test_detail_columns(self):
		columns = [column["fieldname"] for column in execute_detail(self.filters())[0]]
		self.assertEqual(columns[columns.index("voucher_no") + 1], "bill_no")
		self.assertNotIn("remarks", columns)


class TestVATTotalsAndReports(VATRulesTestBase):
	def make_mixed_scenario(self):
		"""Cutoff today: older lines keep the earlier behaviour, today's lines follow the rules."""
		set_cutoff(nowdate())
		older = add_days(nowdate(), -1)
		make_vat_journal_entry(net=100, posting_date=older)
		make_purchase_invoice(rate=111, bill_no=None, posting_date=older)
		make_purchase_journal_entry(vat=45, bill_no=None, party_type=None, posting_date=older)

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
		make_purchase_journal_entry(vat=20, bill_no="K-MIX-JE-R", reduction=True)
		make_purchase_journal_entry(vat=45, bill_no=None, party_type=None)
		make_bank_vat_journal_entry(15)
		make_settlement_journal_entry()
		return add_days(nowdate(), -1)

	def test_detail_has_no_empty_mandatory_cell(self):
		start = self.make_mixed_scenario()
		lines = self.detail(from_date=start)
		self.assertTrue(lines)
		for line in lines:
			for field in MANDATORY:
				self.assertTrue(line[field], f"{field} is empty on {line['voucher_no']}")

	def test_return_totals_equal_detail_sums(self):
		start = self.make_mixed_scenario()
		boxes = self.boxes(from_date=start)
		lines = self.detail(from_date=start)

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
		statuses = {row["status"] for row in self.exceptions(from_date=start).values()}
		self.assertEqual(statuses, {"Excluded", "Included (warning)"})

	def test_exceptions_report_filters(self):
		make_sales_invoice(rate=1000, customer=self.make_customer_without_id())
		make_purchase_invoice(rate=500, bill_no=None)
		make_settlement_journal_entry()

		rows = self.exceptions()
		self.assertEqual({row["side"] for row in rows.values()}, {"Sales", "Purchase"})
		self.assertEqual({row["status"] for row in rows.values()}, {"Excluded", "Included (warning)"})

		self.assertEqual({row["side"] for row in self.exceptions(side="Sales").values()}, {"Sales"})
		self.assertEqual({row["side"] for row in self.exceptions(side="Purchase").values()}, {"Purchase"})

		# one row per voucher and side: the settlement entry has a Sales and a Purchase row (not keyed by voucher)
		_columns, everything = execute_exceptions(self.filters(show_not_reported=1))
		not_reported = [row for row in everything if row["status"] == "Not reported"]
		self.assertEqual(sorted(row["side"] for row in not_reported), ["Purchase", "Sales"])
		self.assertEqual({row["failed_codes"] for row in not_reported}, {"NOT_A_TAXABLE_TRANSACTION"})
		self.assertEqual(
			{row["side"] for row in self.exceptions(side="Sales", show_not_reported=1).values()}, {"Sales"}
		)

	def test_exceptions_report_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts User")
		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, execute_exceptions, self.filters())

	def test_custom_fields_and_setting_exist(self):
		for doctype in ("Purchase Invoice", "Journal Entry"):
			name = f"{doctype}-sijill_buyer_details_verified"
			self.assertTrue(frappe.db.exists("Custom Field", name), name)
			field = frappe.db.get_value(
				"Custom Field", name, ["fieldtype", "allow_on_submit", "no_copy", "module"], as_dict=True
			)
			self.assertEqual((field.fieldtype, field.allow_on_submit), ("Check", 1), name)
			self.assertEqual((field.no_copy, field.module), (1, "Sijill"), name)
			self.assertTrue(frappe.get_meta(doctype).has_field(BUYER_FIELD))

		field = frappe.get_meta("KSA VAT Settings").get_field("output_vat_invoices_only_from")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Date")
