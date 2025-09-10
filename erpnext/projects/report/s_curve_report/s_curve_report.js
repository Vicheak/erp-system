// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["S-Curve Report"] = {
	"filters": [
		{
			"label": __("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 1
		}
	]
};
