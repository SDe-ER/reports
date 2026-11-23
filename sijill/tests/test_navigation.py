# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import json
import unittest

import frappe

from sijill.utils import has_app_permission


class TestNavigation(unittest.TestCase):
	def test_workspace_links_resolve(self):
		workspace = frappe.get_doc("Workspace", "Sijill")
		self.assertEqual(workspace.module, "Sijill")
		self.assertTrue(workspace.public)
		for link in workspace.links:
			if link.type == "Link":
				self.assertTrue(frappe.db.exists(link.link_type, link.link_to), link.link_to)
		for shortcut in workspace.shortcuts:
			self.assertTrue(frappe.db.exists(shortcut.type, shortcut.link_to), shortcut.link_to)
		blocks = json.loads(workspace.content)
		names = {s.label for s in workspace.shortcuts}
		for block in blocks:
			if block["type"] == "shortcut":
				self.assertIn(block["data"]["shortcut_name"], names)

	def test_sidebar_lists_every_report_and_the_settings(self):
		sidebar = frappe.get_doc("Sidebar", "Sijill")
		targets = {(item.link_type, item.link_to) for item in sidebar.items if item.type == "Link"}
		for report in frappe.get_all("Report", filters={"module": "Sijill"}, pluck="name"):
			self.assertIn(("Report", report), targets)
		self.assertIn(("DocType", "KSA VAT Settings"), targets)
		self.assertIn(("Workspace", "Sijill"), targets)

	def test_app_permission(self):
		self.assertTrue(has_app_permission())
