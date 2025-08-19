import frappe

@frappe.whitelist()
def get_latest_rates(item_code, valid_from, is_avg_rate):
    """
    get latest incoming_rate and valuation_rate from Stock Ledger Entry
    """
    # get company from Item Defaults
    company = frappe.db.get_value(
        "Item Default",
        {"parent": item_code},
        "company"
    )
    if not company:
        frappe.throw(f"No default company found for Item {item_code}")

    # get latest Stock Ledger Entry based on valid_from date
    latest_sle = frappe.db.sql("""
        SELECT incoming_rate, valuation_rate
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND company = %s
          AND posting_date <= %s
        ORDER BY posting_date DESC, posting_time DESC, creation DESC
        LIMIT 1
    """, (item_code, company, valid_from), as_dict=True)

    incoming_rate = 0
    average_rate = 0

    if latest_sle:
        incoming_rate = latest_sle[0].incoming_rate or 0
        average_rate = latest_sle[0].valuation_rate or 0

    # cast is_avg_rate to integer
    is_avg_rate = int(is_avg_rate)

    # show specific message if chosen rate type is not found
    if is_avg_rate and not average_rate:
        frappe.msgprint(f"No Average Rate found for Item {item_code} as of {valid_from}")
    if not is_avg_rate and not incoming_rate:
        frappe.msgprint(f"No Incoming Rate found for Item {item_code} as of {valid_from}")

    return {
        "incoming_rate": incoming_rate,
        "average_rate": average_rate
    }
