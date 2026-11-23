// Copyright (c) 2026, SDCE and contributors
// For license information, please see license.txt

frappe.provide("erpnext.ksa_vat_return");

erpnext.ksa_vat_return.quarter_start = function () {
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const month = Math.floor(today.getMonth() / 3) * 3;
	return frappe.datetime.obj_to_str(new Date(today.getFullYear(), month, 1));
};

erpnext.ksa_vat_return.detail_url = function (data) {
	const filters = frappe.query_report.get_filter_values();
	const params = {
		company: filters.company,
		from_date: filters.from_date,
		to_date: filters.to_date,
		side: data.side === "All" ? "" : data.side,
		category: data.category || "",
		rate: data.rate || "",
	};
	const query = Object.keys(params)
		.filter((key) => params[key])
		.map((key) => `${key}=${encodeURIComponent(params[key])}`)
		.join("&");
	return `/app/query-report/${encodeURIComponent("KSA VAT Return Detail")}?${query}`;
};

frappe.query_reports["KSA VAT Return"] = {
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
			default: erpnext.ksa_vat_return.quarter_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_days(
				frappe.datetime.add_months(erpnext.ksa_vat_return.quarter_start(), 3),
				-1
			),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		if (column.fieldname === "legend") {
			const text = frappe.utils.escape_html(value || "");
			if (data.is_heading) return `<span class="text-muted">${text}</span>`;
			return data.bold ? `<b>${text}</b>` : text;
		}

		// fields without a value in the return stay blank, as in the official form
		if (["amount", "adjustment", "vat_amount"].includes(column.fieldname) && value == null) {
			return "";
		}

		let formatted = default_formatter(value, row, column, data);
		if (data.side && ["amount", "adjustment", "vat_amount"].includes(column.fieldname)) {
			formatted = `<a href="${erpnext.ksa_vat_return.detail_url(data)}">${formatted}</a>`;
		}
		return data.bold ? `<b>${formatted}</b>` : formatted;
	},
};
