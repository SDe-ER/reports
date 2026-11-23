// Copyright (c) 2026, SDCE and contributors
// For license information, please see license.txt

frappe.query_reports["KSA VAT Return Detail"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
			get_query: () => ({ filters: { country: "Saudi Arabia" } }),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "side",
			label: __("Sales / Purchase"),
			fieldtype: "Select",
			options: ["", "Sales", "Purchase"],
		},
		{
			fieldname: "category",
			label: __("VAT Category"),
			fieldtype: "Select",
			options: [
				"",
				"Standard Rated Sales",
				"Zero Rated Domestic Sales",
				"Exports",
				"Standard Rated Purchases",
				"Zero Rated Purchases",
			],
		},
		{
			fieldname: "rate",
			label: __("Rate (%)"),
			fieldtype: "Float",
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Select",
			options: ["", "Customer", "Supplier"],
			on_change: () => frappe.query_report.set_filter_value("party", ""),
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			options: "party_type",
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type", null, "KSA VAT Return"),
			fieldtype: "Select",
			options: ["", "Sales Invoice", "Purchase Invoice", "Journal Entry", "Payment Entry"],
		},
		{
			fieldname: "show_excluded",
			label: __("Show Excluded Entries"),
			fieldtype: "Check",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		let formatted = default_formatter(value, row, column, data);
		if (column.fieldname === "category" && value) {
			formatted = __(value);
		}
		if (data && data.remarks && column.fieldname !== "remarks") {
			formatted = `<span class="text-muted">${formatted}</span>`;
		}
		return formatted;
	},
};
