# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import unittest
from pathlib import Path

import frappe
from babel.messages.pofile import read_po


def read_catalog(path):
	with open(path, "rb") as f:
		return read_po(f)


class TestTranslations(unittest.TestCase):
	def test_no_override_of_core_translations(self):
		"""Sijill loads after Frappe and ERPNext: a string without a context that they already translate would
		replace their Arabic label on every screen of the site. Report-specific wording must use a context."""
		own = read_catalog(Path(frappe.get_app_path("sijill", "locale", "ar.po")))
		core_ids = set()
		for app in ("frappe", "erpnext", "hrms"):
			try:
				path = Path(frappe.get_app_path(app, "locale", "ar.po"))
			except Exception:
				continue
			if path.exists():
				core_ids |= {m.id for m in read_catalog(path) if m.id and not m.context}

		overrides = sorted(m.id for m in own if m.id and not m.context and m.id in core_ids)
		self.assertEqual(overrides, [], "Use a translation context for these strings")
