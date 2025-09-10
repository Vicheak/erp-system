# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 200},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": _("Qty UBL"), "fieldname": "qty_ubl", "fieldtype": "Data", "width": 100},

        # Sales Order column
        {"label": _("SO Qty"), "fieldname": "so_qty", "fieldtype": "Float", "width": 150},
        {"label": _("SO Rate"), "fieldname": "so_rate", "fieldtype": "Currency", "width": 150},
        {"label": _("SO Amount"), "fieldname": "so_amount", "fieldtype": "Currency", "width": 170},

        # Planned Material Request column
        {"label": _("Planned Qty"), "fieldname": "planned_qty", "fieldtype": "Float", "width": 150},
        {"label": _("Planned Rate"), "fieldname": "planned_rate", "fieldtype": "Currency", "width": 150},
        {"label": _("Planned Amount"), "fieldname": "planned_amount", "fieldtype": "Currency", "width": 170},
        {"label": _("Diff Planned Qty"), "fieldname": "diff_planned_qty", "fieldtype": "Float", "width": 200},
        {"label": _("Diff Planned Rate"), "fieldname": "diff_planned_rate", "fieldtype": "Currency", "width": 200},
        {"label": _("Diff Planned Amount"), "fieldname": "diff_planned_amount", "fieldtype": "Currency", "width": 220},

        # Actual Material Request column
        {"label": _("Actual Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 150},
        {"label": _("Actual Rate"), "fieldname": "actual_rate", "fieldtype": "Currency", "width": 150},
        {"label": _("Actual Amount"), "fieldname": "actual_amount", "fieldtype": "Currency", "width": 170},
        {"label": _("Diff Actual Qty"), "fieldname": "diff_actual_qty", "fieldtype": "Float", "width": 200},
        {"label": _("Diff Actual Rate"), "fieldname": "diff_actual_rate", "fieldtype": "Currency", "width": 200},
        {"label": _("Diff Actual Amount"), "fieldname": "diff_actual_amount", "fieldtype": "Currency", "width": 220},
    ]

def get_data(filters):
    data = []

    # --- Sales Order Items ---
    so_items = frappe.db.sql(f"""
        SELECT so.project as project,
			   soi.parent as sales_order,
			   soi.item_code as item_code,
			   soi.item_name as item_name,
			   soi.uom as uom,
			   soi.custom_quantity_ubl as qty_ubl,
               soi.qty as so_qty,
			   soi.rate as so_rate,
			   soi.amount as so_amount
        FROM `tabSales Order` so
        JOIN `tabSales Order Item` soi 
		ON so.name = soi.parent
        WHERE so.docstatus = 1 AND soi.parenttype = 'Sales Order' 
			{ "AND so.project = %(project)s" if filters.get("project") else "" }
			{ "AND so.name = %(sales_order)s" if filters.get("sales_order") else "" }
            { "AND soi.item_code = %(task)s" if filters.get("task") else "" }
		ORDER BY so.name ASC, soi.idx ASC
    """, filters, as_dict=True)

    # --- Planned Material Requests ---
    planned = frappe.db.sql(f"""
        SELECT mr.project as project,
		       mri.item_code as item_code,
               SUM(mri.qty) as planned_qty,
			   AVG(mri.rate) as planned_rate,
			   SUM(mri.amount) as planned_amount
        FROM `tabMaterial Request` mr
        JOIN `tabMaterial Request Item` mri 
		ON mr.name = mri.parent
        WHERE mr.docstatus = 1 AND mri.parenttype = 'Material Request'
            AND mr.material_request_type = 'Plan'
			{ "AND mr.project = %(project)s" if filters.get("project") else "" }
            { "AND mri.item_code = %(task)s" if filters.get("task") else "" }
        GROUP BY mr.project, mri.item_code
		ORDER BY mr.name ASC, mri.idx ASC
    """, filters, as_dict=True)
    planned_map = {(p.project, p.item_code): p for p in planned}

    # --- Actual Material Requests ---
    actual = frappe.db.sql(f"""
        SELECT mr.project as project,
			   mri.item_code as item_code,
               SUM(mri.qty) as actual_qty,
			   AVG(mri.rate) as actual_rate,
			   SUM(mri.amount) as actual_amount
        FROM `tabMaterial Request` mr
        JOIN `tabMaterial Request Item` mri
		ON mr.name = mri.parent
		WHERE mr.docstatus = 1 AND mri.parenttype = 'Material Request'
            AND mr.material_request_type != 'Plan'
        	{ "AND mr.project = %(project)s" if filters.get("project") else "" }
            { "AND mri.item_code = %(task)s" if filters.get("task") else "" }
        GROUP BY mr.project, mri.item_code
		ORDER BY mr.name ASC, mri.idx ASC
    """, filters, as_dict=True)
    actual_map = {(a.project, a.item_code): a for a in actual}

    # --- merge data ---
    for so in so_items:
        planned_row = planned_map.get((so.project, so.item_code), {})
        actual_row = actual_map.get((so.project, so.item_code), {})

        planned_qty = planned_row["planned_qty"] if planned_row else None
        planned_rate = planned_row["planned_rate"] if planned_row else None
        planned_amount = planned_row["planned_amount"] if planned_row else None

        actual_qty = actual_row["actual_qty"] if actual_row else None
        actual_rate = actual_row["actual_rate"] if actual_row else None
        actual_amount = actual_row["actual_amount"] if actual_row else None

        # --- differences ---
        if planned_row:
            diff_planned_qty = so.so_qty - planned_qty
            diff_planned_rate = so.so_rate - planned_rate
            diff_planned_amount = so.so_amount - planned_amount
        else:
            diff_planned_qty = 0
            diff_planned_rate = 0
            diff_planned_amount = 0

        if actual_row:
            diff_actual_qty = so.so_qty - actual_qty
            diff_actual_rate = so.so_rate - actual_rate
            diff_actual_amount = so.so_amount - actual_amount
        else:
            diff_actual_qty = 0
            diff_actual_rate = 0
            diff_actual_amount = 0

        data.append({
            "project": so.project,
            "sales_order": so.sales_order,
            "item_code": so.item_code,
            "item_name": so.item_name,
            "uom": so.uom,
            "qty_ubl": so.qty_ubl,

            "so_qty": so.so_qty,
            "so_rate": so.so_rate,
            "so_amount": so.so_amount,

            "planned_qty": planned_qty,
            "planned_rate": planned_rate,
            "planned_amount": planned_amount,
            "diff_planned_qty": diff_planned_qty,
            "diff_planned_rate": diff_planned_rate,
            "diff_planned_amount": diff_planned_amount,

            "actual_qty": actual_qty,
            "actual_rate": actual_rate,
            "actual_amount": actual_amount,
            "diff_actual_qty": diff_actual_qty,
            "diff_actual_rate": diff_actual_rate,
            "diff_actual_amount": diff_actual_amount,
        })

    return data
