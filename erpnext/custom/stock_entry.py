import frappe

def set_item_accounts(doc, method):
    if not doc.items:
        return

    # get the company default accounts
    company = frappe.get_doc("Company", doc.company)

    # priority: Default Operating Cost Account > Stock Adjustment Account
    default_expense_account = (
        company.default_operating_cost_account or
        company.stock_adjustment_account
    )

    # fallback check in case both are None (optional safety)
    if not default_expense_account:
        frappe.throw(f"No default expense account found for company {doc.company}")

    for item in doc.items:
        if not item.expense_account:
            # no account set, use fallback
            item.expense_account = default_expense_account
            continue

        # check if the account is of type "Cost of Goods Sold"
        account_type = frappe.get_cached_value("Account", item.expense_account, "account_type")

        if account_type == "Cost of Goods Sold":
            # replace COGS account to avoid warning
            item.expense_account = default_expense_account

        # always set cost center if available
        item.cost_center = company.cost_center or None

def set_scrap_items_target_warehouse(doc, method):
    if doc.stock_entry_type != "Manufacture":
        return
    if not doc.from_bom or not doc.bom_no:
        return

    # load BOM doc with scrap_items
    bom = frappe.get_doc("BOM", doc.bom_no)

    # build map: item_code → BOM Scrap Item
    scrap_map = {scrap.item_code: scrap for scrap in bom.scrap_items}

    for item in doc.items:
        if item.is_scrap_item:
            scrap_item = scrap_map.get(item.item_code)
            if not scrap_item:
                continue

            # load full Item doc (with child tables)
            item_doc = frappe.get_doc("Item", item.item_code)

            # search for default_warehouse in item_defaults for this company
            default_warehouse = None
            for d in item_doc.get("item_defaults", []):
                if d.company == doc.company:
                    default_warehouse = d.default_warehouse
                    break

            if default_warehouse:
                item.t_warehouse = default_warehouse

def set_serial_no_metadata(doc, method):
    if doc.stock_entry_type != "Material Receipt":
        return

    for item in doc.items:
        if not item.serial_no:
            continue

        # extract lists
        serial_nos = [s.strip() for s in item.serial_no.strip().split('\n') if s.strip()]
        engine_nos = [e.strip() for e in (item.get("custom_engine_no") or "").strip().split('\n')]
        colors = [c.strip() for c in (item.get("custom_color") or "").strip().split('\n')]
        years = [y.strip() for y in (item.get("custom_year") or "").strip().split('\n')]

        # validate that all lists have the same length
        if not (len(serial_nos) == len(engine_nos) == len(colors) == len(years)):
            frappe.throw(
                f"Mismatch in count of Serial No, Engine No, Color, or Year for item {item.item_code}"
            )

        for i in range(len(serial_nos)):
            serial_no = serial_nos[i]
            engine_no = engine_nos[i]
            color = colors[i]
            year = years[i]

            serial_doc = frappe.get_doc("Serial No", serial_no)
            # force save
            serial_doc.db_set("custom_engine_no", engine_no, update_modified=True)
            serial_doc.db_set("custom_color", color, update_modified=True)
            serial_doc.db_set("custom_year", year, update_modified=True)
