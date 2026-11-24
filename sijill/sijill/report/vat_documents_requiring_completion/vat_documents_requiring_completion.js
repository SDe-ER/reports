// Copyright (c) 2026, SDCE and contributors
// For license information, please see license.txt

frappe.query_reports["VAT Documents Requiring Completion"] = {
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
			default: quarter_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.add_months(quarter_start(), 3), -1),
		},
		{
			fieldname: "side",
			label: __("Sales / Purchase"),
			fieldtype: "Select",
			options: ["", "Sales", "Purchase"],
		},
		{
			fieldname: "show_not_reported",
			label: __("Include settlement and opening entries"),
			fieldtype: "Check",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		if (column.fieldname === "open") {
			const url = frappe.utils.get_form_link(data.voucher_type, data.voucher_no);
			return `<a href="${frappe.utils.escape_html(url)}">${frappe.utils.escape_html(__("Open"))}</a>`;
		}
		if (["status", "side"].includes(column.fieldname) && value) {
			return frappe.utils.escape_html(__(value));
		}
		if (["failed_codes", "failed_rules_en", "failed_rules_ar"].includes(column.fieldname)) {
			return frappe.utils.escape_html(value || "");
		}
		return default_formatter(value, row, column, data);
	},
};

function quarter_start() {
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const month = Math.floor(today.getMonth() / 3) * 3;
	return frappe.datetime.obj_to_str(new Date(today.getFullYear(), month, 1));
}
