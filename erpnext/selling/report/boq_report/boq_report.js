// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["BOQ Report"] = {
	"filters": [
		{
			"label": __("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 1
		},
		{
			"label": __("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"reqd": 0,
			"get_query": function() {
				var project = frappe.query_report.get_filter_value("project");
				if (project) {
					return {
						filters: {
							"project": project
						}
					};
				}
			}
		},
		{
			"label": __("Task"),
			"fieldname": "task",
			"fieldtype": "Link",
			"options": "Task",
			"reqd": 0,
			"get_query": function() {
				var project = frappe.query_report.get_filter_value("project");
				if (project) {
					return {
						filters: {
							"project": project
						}
					};
				}
			}
		}
	]
};
