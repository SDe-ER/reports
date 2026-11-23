# Copyright (c) 2026, SDCE and contributors
# For license information, please see license.txt

import frappe

APP_ROLES = ("Accounts User", "Accounts Manager", "Auditor", "System Manager")


def has_app_permission():
	"""Show Sijill on the apps screen to the users who can run its reports."""
	if frappe.session.user == "Administrator":
		return True
	if frappe.get_cached_value("User", frappe.session.user, "user_type") == "Website User":
		return False
	return bool(set(APP_ROLES) & set(frappe.get_roles()))
