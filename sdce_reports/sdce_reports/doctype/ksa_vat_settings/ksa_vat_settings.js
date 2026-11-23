// Copyright (c) 2026, SDCE and contributors
// For license information, please see license.txt

frappe.ui.form.on("KSA VAT Settings", {
	onload(frm) {
		frm.set_query("company", () => ({ filters: { country: "Saudi Arabia" } }));
		frm.set_query("account", "ksa_vat_accounts", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},
});
