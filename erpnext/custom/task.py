import frappe
from frappe.utils import flt, safe_div

def update_task_group_progress(doc, method):
    """ 
    if group, recalc itself & bubble up.
    if not a group, recalc its parent.
    """
    if doc.is_group:
        execute_progress_rollup(doc.name, updated_doc=doc)
    elif doc.parent_task:
        execute_progress_rollup(doc.parent_task, updated_doc=doc)

def execute_progress_rollup(task_name, updated_doc=None):
    """recalculate progress for a task group and bubble up recursively"""
    task = frappe.get_doc("Task", task_name)

    # only recalc for group and task within project
    if not task.is_group or not task.project:
        return

    # get parent project to check % complete method
    project = frappe.get_doc("Project", task.project)
    complete_method = project.percent_complete_method

    # fetch direct children (both groups & leaf tasks)
    child_tasks = frappe.get_all(
        "Task",
        filters={"parent_task": task.name},
        fields=["name", "progress", "status", "task_weight", "is_group"]
    )

    if not child_tasks:
        task.progress = 0
    else:
        # replace stale child with current in-memory doc
        if updated_doc and updated_doc.parent_task == task.name:
            for child in child_tasks:
                if child["name"] == updated_doc.name:
                    child["progress"] = updated_doc.progress
                    child["status"] = updated_doc.status
                    child["task_weight"] = updated_doc.task_weight
                    break

        total = len(child_tasks)
        completed = sum(1 for t in child_tasks if t.status in ("Completed", "Cancelled"))
        sum_progress = sum(flt(t.progress) for t in child_tasks)
        weight_sum = sum(flt(t.task_weight) for t in child_tasks if t.task_weight)

        pct_complete = 0

        # --- apply same formulas as project ---
        if complete_method == "Task Completion" and total > 0:
            pct_complete = flt(completed / total * 100, 2)

        elif complete_method == "Task Progress" and total > 0:
            pct_complete = flt(sum_progress / total, 2)

        elif complete_method == "Task Weight" and weight_sum > 0:
            for t in child_tasks:
                pct_complete += flt(t.progress) * safe_div(flt(t.task_weight), weight_sum)
            pct_complete = flt(pct_complete, 2)

        else: # fallback
            pct_complete = flt(sum_progress / total, 2) if total > 0 else 0
            
        # update progress
        task.db_set("progress", pct_complete, update_modified=False)

    # bubble up to parent recursively
    if task.parent_task:
        execute_progress_rollup(task.parent_task)
