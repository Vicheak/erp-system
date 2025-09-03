import frappe
from frappe import _

def validate_mr(doc, method):
    is_plan = doc.material_request_type == "Plan"
    mr_project = doc.project

    if is_plan:
        # check if each item's project & task match header
        for item in doc.items:
            if item.project != mr_project:
                frappe.throw(_("Item {0}: Project mismatch with Material Request Project").format(item.item_code))
            if not item.task:
                frappe.throw(_("Item {0}: Task is required for planned Material Request").format(item.item_code))

            # ensure the task belongs to the selected project
            task_project = frappe.db.get_value("Task", item.task, "project")
            if task_project != mr_project:
                frappe.throw(_("Item {0}: Task {1} does not belong to Project {2}").format(item.item_code, item.task, mr_project))
    else:
        # fetch all approved Plan MRs for same project
        plan_mrs = frappe.get_all("Material Request", 
            filters={
                "material_request_type": "Plan",
                "project": mr_project,
                "docstatus": 1,
                "workflow_state": "Approved"
            },
            fields=["name"]
        )

        if not plan_mrs:
            frappe.throw(_("No approved planned Material Requests found for project {0}").format(mr_project))

        plan_mr_names = [mr.name for mr in plan_mrs]

        # fetch all items from plan MRs
        plan_items = frappe.get_all("Material Request Item",
            filters={"parent": ["in", plan_mr_names]},
            fields=["item_code", "project", "task", "qty"]
        )

        from collections import defaultdict

        planned_qty_map = defaultdict(float)
        item_plan_info = {}

        for pi in plan_items:
            planned_qty_map[pi.item_code] += pi.qty
            if pi.item_code not in item_plan_info:
                item_plan_info[pi.item_code] = {"project": pi.project, "task": pi.task}

        daily_qty_map = defaultdict(float)
        for item in doc.items:
            daily_qty_map[item.item_code] += item.qty

        # now validate each item in Daily MR
        for item in doc.items:
            code = item.item_code

            if code not in planned_qty_map:
                frappe.throw(_("Item {0} not found in any approved Planned Material Request for project {1}").format(code, mr_project))

            plan_info = item_plan_info.get(code)

            if item.project != plan_info["project"]:
                frappe.throw(_("Item {0}: Project mismatch with Planned MR item").format(code))

            if item.task != plan_info["task"]:
                frappe.throw(_("Item {0}: Task mismatch with Planned MR item").format(code))

            if item.project != mr_project:
                frappe.throw(_("Item {0}: Project mismatch with Material Request Project").format(code))

            # ensure task belongs to the selected project
            if not item.task:
                frappe.throw(_("Item {0}: Task is required for Daily Material Request").format(code))

            task_project = frappe.db.get_value("Task", item.task, "project")
            if task_project != mr_project:
                frappe.throw(_("Item {0}: Task {1} does not belong to Project {2}").format(code, item.task, mr_project))

            # check quantity not exceeding planned
            total_daily_qty = frappe.db.sql("""
                SELECT SUM(qty) FROM `tabMaterial Request Item`
                WHERE item_code = %s AND parent IN (
                    SELECT name FROM `tabMaterial Request`
                    WHERE project = %s AND material_request_type != 'Plan' AND docstatus = 1
                )
            """, (code, mr_project))[0][0] or 0

            total_after_this = total_daily_qty + daily_qty_map[code]

            if total_after_this > planned_qty_map[code]:
                frappe.throw(_("Item {0}: Requested quantity exceeds total planned quantity ({1} > {2})").format(code, total_after_this, planned_qty_map[code]))
