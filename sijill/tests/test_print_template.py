# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import re
import unittest
from pathlib import Path

import frappe


def template():
	path = Path(frappe.get_app_path("sijill", "sijill", "report", "ksa_vat_return", "ksa_vat_return.html"))
	return path.read_text(encoding="utf-8")


class TestPrintTemplate(unittest.TestCase):
	def test_greys_win_over_the_site_print_style(self):
		"""A site Print Style may set table header and cell colours with !important. The approved greys are set
		on Sijill's own classes, with more class selectors and !important, so they win inside this print only."""
		html = template()
		self.assertRegex(
			html,
			r"\.ksa-vat \.kv-rows thead th\.kv-h \{[^}]*background: #f3f3f3 !important;[^}]*color: #171717 !important;",
		)
		self.assertRegex(html, r"\.ksa-vat \.kv-rows tbody td\.kv-d \{[^}]*color: #171717 !important;")
		self.assertRegex(html, r"tr\.kv-total td\.kv-d \{[^}]*background: #f3f3f3 !important;")
		self.assertRegex(html, r"tr\.kv-heading td\.kv-d \{[^}]*background: #fafafa !important;")
		self.assertRegex(html, r"td\.kv-d \{ border: 1px solid #d1d8dd !important; \}")
		# every header and body cell of the return table carries the class the rules target
		self.assertNotRegex(html, r"<th\b(?![^>]*\bkv-h\b)[^>]*>", "a table header cell without kv-h")
		rows = html.split('<table class="kv-rows">', 1)[1].split("</table>", 1)[0]
		self.assertNotRegex(rows, r"<td\b(?![^>]*\bkv-d\b)[^>]*>", "a table body cell without kv-d")

	def test_rules_stay_scoped_to_sijill(self):
		"""No rule may style the page outside the .ksa-vat block (the site Print Style and Letter Heads stay as
		they are)."""
		css = template().split("<style>", 1)[1].split("</style>", 1)[0]
		css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
		for selector_list in re.findall(r"([^{}]+)\{", css):
			for selector in selector_list.split(","):
				selector = selector.strip()
				if selector.startswith("@page"):
					continue
				self.assertRegex(selector, r"^\.ksa-vat(?=[\s.\[:#>]|$)", selector)

	def test_company_line_without_company_row(self):
		"""The company is printed once above the title; the label / value block does not repeat it."""
		html = template()
		self.assertIn('<div class="kv-co">', html)
		meta = html.split('<table class="kv-meta">', 1)[1].split("</table>", 1)[0]
		self.assertNotIn('__("Company")', meta)
		for label in (
			'__("VAT Registration Number", null, CTX)',
			'__("From Date")',
			'__("To Date")',
			'__("Issue Date", null, CTX)',
		):
			self.assertIn(label, meta)
