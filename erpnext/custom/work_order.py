import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime

def validate_workstation(doc, method):
    """
    validate workstation status and downtime entries before Work Order submission
    """
    if not doc.operations:
        return
    
    # get all unique workstations from operations
    workstations = set()
    for operation in doc.operations:
        if operation.workstation:
            workstations.add(operation.workstation)
    
    # validate each workstation
    for workstation_name in workstations:
        validate_single_workstation(workstation_name, doc.name)

def validate_single_workstation(workstation_name, work_order_name):
    """
    validate individual workstation status and downtime
    """
    # get workstation document
    workstation = frappe.get_doc("Workstation", workstation_name)
    
    # check if workstation status is "Production"
    if workstation.status != "Production":
        # check for active downtime entries
        current_time = now_datetime()
        
        # get active downtime entries for this workstation
        active_downtime = frappe.db.sql("""
            SELECT name, from_time, to_time, stop_reason
            FROM `tabDowntime Entry`
            WHERE workstation = %s
            AND docstatus = 0
            AND from_time <= %s
            AND (to_time IS NULL OR to_time >= %s)
            ORDER BY from_time DESC
            LIMIT 1
        """, (workstation_name, current_time, current_time), as_dict=True)
        
        if active_downtime:
            downtime_entry = active_downtime[0]
            
            # workstation is still in downtime
            downtime_reason = downtime_entry.get("stop_reason", "Unknown")
            if downtime_entry.to_time:
                end_time = frappe.format(downtime_entry.to_time, {"fieldtype": "Datetime"})
                error_msg = _("Cannot submit Work Order {0}. Workstation {1} is currently down due to '{2}' until {3}.").format(
                    work_order_name, workstation_name, downtime_reason, end_time
                )
            else:
                error_msg = _("Cannot submit Work Order {0}. Workstation {1} is currently down due to '{2}' with no specified end time.").format(
                    work_order_name, workstation_name, downtime_reason
                )
            
            frappe.throw(error_msg, title=_("Workstation Not Available"))
        else:
            # no active downtime but status is not Production
            frappe.throw(
                _("Cannot submit Work Order {0}. Workstation {1} status is '{2}'. Only workstations with 'Production' status are allowed.").format(
                    work_order_name, workstation_name, workstation.status
                ),
                title=_("Workstation Status not in Production")
            )
