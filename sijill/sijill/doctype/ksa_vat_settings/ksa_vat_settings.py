# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_region
from frappe import _
from frappe.model.document import Document


class KSAVATSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from sijill.sijill.doctype.ksa_vat_account.ksa_vat_account import KSAVATAccount

		company: DF.Link
		ksa_vat_accounts: DF.Table[KSAVATAccount]
	# end: auto-generated types

	def validate(self):
		self.validate_company_region()
		self.validate_accounts()

	def validate_company_region(self):
		if self.company and get_region(self.company) != "Saudi Arabia":
			frappe.throw(_("Company {0} is not in Saudi Arabia.").format(frappe.bold(self.company)))

	def validate_accounts(self):
		accounts = set()
		for row in self.ksa_vat_accounts:
			if row.account in accounts:
				frappe.throw(_("Row #{0}: Account {1} is added more than once").format(row.idx, row.account))
			company, is_group = frappe.get_cached_value("Account", row.account, ["company", "is_group"])
			if company != self.company:
				frappe.throw(
					_("Row #{0}: Account {1} does not belong to company {2}").format(
						row.idx, row.account, self.company
					)
				)
			if is_group:
				frappe.throw(_("Row #{0}: Account {1} is a group account").format(row.idx, row.account))
			accounts.add(row.account)

		types = {row.vat_account_type for row in self.ksa_vat_accounts}
		for required in ("Output VAT", "Input VAT"):
			if required not in types:
				frappe.throw(_("Add at least one account of type {0}").format(frappe.bold(_(required))))


def get_ksa_vat_accounts(company):
	"""Returns {account: vat_account_type} for the company, or an empty dict when not configured."""
	return dict(
		frappe.get_all(
			"KSA VAT Account",
			filters={"parent": company, "parenttype": "KSA VAT Settings"},
			fields=["account", "vat_account_type"],
			as_list=True,
		)
	)
