import frappe
from frappe import _

def validate_multiple_payment_modes(doc, method):
    """validate multiple payment modes before submission"""
    
    # check if custom payment mode is configured
    if doc.custom_mode_of_payment_1:
        if not doc.custom_account_paid_to_1:
            frappe.throw(_("Please select Account Paid To (1) for Mode of Payment (1): {0}").format(doc.custom_mode_of_payment_1))
        
        if not doc.custom_paid_amount_1 or doc.custom_paid_amount_1 <= 0:
            frappe.throw(_("Please enter a valid Paid Amount (1) for Mode of Payment (1): {0}").format(doc.custom_mode_of_payment_1))
    
    # validate that mode of payments are different
    mode_of_payments = []
    if doc.mode_of_payment:
        mode_of_payments.append(doc.mode_of_payment)
    if doc.custom_mode_of_payment_1:
        mode_of_payments.append(doc.custom_mode_of_payment_1)
    
    if len(mode_of_payments) != len(set(mode_of_payments)):
        frappe.throw(_("Mode of Payment cannot be the same. Please select different modes of payment."))

def create_additional_gl_entries(doc, method):
    """create additional GL entries for custom payment modes"""
    
    if not (doc.custom_mode_of_payment_1 and doc.custom_account_paid_to_1 and doc.custom_paid_amount_1):
        return
    
    # calculate total amount
    total_amount = doc.paid_amount + doc.custom_paid_amount_1
    
    # get account currency for custom account
    custom_account_currency = frappe.get_cached_value("Account", doc.custom_account_paid_to_1, "account_currency")
    
    # create GL Entry document object
    gl_entry_doc = frappe.new_doc("GL Entry")
    
    # set all required fields
    gl_entry_doc.update({
        "posting_date": doc.posting_date,
        "transaction_date": None,
        "fiscal_year": frappe.get_cached_value("Company", doc.company, "default_fiscal_year"),
        "account": doc.custom_account_paid_to_1,
        "account_currency": custom_account_currency,
        "against": doc.party,
        "party_type": None,
        "party": None,
        "voucher_type": doc.doctype,
        "voucher_no": doc.name,
        "voucher_subtype": doc.payment_type,
        "transaction_currency": None,
        "against_voucher_type": None,
        "against_voucher": None,
        "voucher_detail_no": None,
        "transaction_exchange_rate": 0.0,
        "cost_center": doc.cost_center,
        "project": doc.project,
        "finance_book": None,
        "company": doc.company,
        "is_opening": "No",
        "is_advance": "No",
        "to_rename": 1,
        "is_cancelled": 0,
        "remarks": f"Amount USD {doc.custom_paid_amount_1} received from {doc.party} via {doc.custom_mode_of_payment_1}"
    })
    
    # set debit/credit based on payment type
    if doc.payment_type == "Receive":
        gl_entry_doc.update({
            "debit": doc.custom_paid_amount_1,
            "debit_in_account_currency": doc.custom_paid_amount_1,
            "debit_in_transaction_currency": doc.custom_paid_amount_1,
            "credit": 0.0,
            "credit_in_account_currency": 0.0,
            "credit_in_transaction_currency": 0.0
        })
    else:
        gl_entry_doc.update({
            "debit": 0.0,
            "debit_in_account_currency": 0.0,
            "debit_in_transaction_currency": 0.0,
            "credit": doc.custom_paid_amount_1,
            "credit_in_account_currency": doc.custom_paid_amount_1,
            "credit_in_transaction_currency": doc.custom_paid_amount_1
        })
    
    # insert and submit the GL Entry
    gl_entry_doc.insert(ignore_permissions=True)
    gl_entry_doc.submit()
    
    # update the existing Debtors/Creditors GL entry to reflect total amount
    update_main_account_gl_entry(doc, total_amount)

def update_main_account_gl_entry(doc, total_amount):
    """update the main account (Debtors/Creditors) GL entry with total amount"""
    
    main_account = doc.paid_from if doc.payment_type == "Receive" else doc.paid_to
    against_accounts = f"{doc.paid_to},{doc.custom_account_paid_to_1}" if doc.payment_type == "Receive" else f"{doc.paid_from},{doc.custom_account_paid_to_1}"
    
    # update the main account GL entry
    if doc.payment_type == "Receive":
        frappe.db.sql("""
            UPDATE `tabGL Entry` 
            SET credit = %s, 
                credit_in_account_currency = %s,
                credit_in_transaction_currency = %s,
                against = %s,
                modified = NOW(),
                modified_by = %s
            WHERE voucher_no = %s 
            AND account = %s
            AND voucher_type = %s
            AND is_cancelled = 0
        """, (
            total_amount, total_amount, total_amount, against_accounts,
            frappe.session.user, doc.name, main_account, doc.doctype
        ))
    else:
        frappe.db.sql("""
            UPDATE `tabGL Entry` 
            SET debit = %s, 
                debit_in_account_currency = %s,
                debit_in_transaction_currency = %s,
                against = %s,
                modified = NOW(),
                modified_by = %s
            WHERE voucher_no = %s 
            AND account = %s
            AND voucher_type = %s
            AND is_cancelled = 0
        """, (
            total_amount, total_amount, total_amount, against_accounts,
            frappe.session.user, doc.name, main_account, doc.doctype
        ))

def cancel_additional_gl_entries(doc, method):
    """handle cancellation of additional GL entries"""
    
    if not (doc.custom_mode_of_payment_1 and doc.custom_account_paid_to_1 and doc.custom_paid_amount_1):
        return
    
    # calculate total amount
    total_amount = doc.paid_amount + doc.custom_paid_amount_1
    
    # create cancellation GL Entry for the custom payment mode
    custom_account_currency = frappe.get_cached_value("Account", doc.custom_account_paid_to_1, "account_currency")
    
    # create GL Entry document object for cancellation
    cancel_gl_entry_doc = frappe.new_doc("GL Entry")
    
    # set all required fields
    cancel_gl_entry_doc.update({
        "posting_date": doc.posting_date,
        "transaction_date": None,
        "fiscal_year": frappe.get_cached_value("Company", doc.company, "default_fiscal_year"),
        "account": doc.custom_account_paid_to_1,
        "account_currency": custom_account_currency,
        "against": doc.party,
        "party_type": None,
        "party": None,
        "voucher_type": doc.doctype,
        "voucher_no": doc.name,
        "voucher_subtype": doc.payment_type,
        "transaction_currency": None,
        "against_voucher_type": None,
        "against_voucher": None,
        "voucher_detail_no": None,
        "transaction_exchange_rate": 0.0,
        "cost_center": doc.cost_center,
        "project": doc.project,
        "finance_book": None,
        "company": doc.company,
        "is_opening": "No",
        "is_advance": "No",
        "to_rename": 1,
        "is_cancelled": 1, # mark as cancelled
        "remarks": f"Cancelled: Amount USD {doc.custom_paid_amount_1} from {doc.party} via {doc.custom_mode_of_payment_1}"
    })
    
    # set debit/credit opposite to the original entry (for cancellation)
    if doc.payment_type == "Receive":
        # original was debit, so cancellation is credit
        cancel_gl_entry_doc.update({
            "debit": 0.0,
            "debit_in_account_currency": 0.0,
            "debit_in_transaction_currency": 0.0,
            "credit": doc.custom_paid_amount_1,
            "credit_in_account_currency": doc.custom_paid_amount_1,
            "credit_in_transaction_currency": doc.custom_paid_amount_1
        })
    else:
        # original was credit, so cancellation is debit
        cancel_gl_entry_doc.update({
            "debit": doc.custom_paid_amount_1,
            "debit_in_account_currency": doc.custom_paid_amount_1,
            "debit_in_transaction_currency": doc.custom_paid_amount_1,
            "credit": 0.0,
            "credit_in_account_currency": 0.0,
            "credit_in_transaction_currency": 0.0
        })
    
    # insert the cancellation GL Entry (no need to submit as it's a cancellation entry)
    cancel_gl_entry_doc.insert(ignore_permissions=True)
    cancel_gl_entry_doc.submit()
    
    # also mark the original custom GL entry as cancelled
    frappe.db.sql("""
        UPDATE `tabGL Entry` 
        SET is_cancelled = 1,
            modified = NOW(),
            modified_by = %s
        WHERE voucher_no = %s 
        AND account = %s
        AND voucher_type = %s
        AND is_cancelled = 0
    """, (
        frappe.session.user, doc.name, doc.custom_account_paid_to_1, doc.doctype
    ))
    
    # revert the main account GL entry to original amount
    revert_main_account_gl_entry(doc, total_amount)

def revert_main_account_gl_entry(doc, total_amount):
    """revert the main account (Debtors/Creditors) GL entry to original amount"""
    
    main_account = doc.paid_from if doc.payment_type == "Receive" else doc.paid_to
    
    # keep the same against accounts format as during submission
    against_accounts = f"{doc.paid_to},{doc.custom_account_paid_to_1}" if doc.payment_type == "Receive" else f"{doc.paid_from},{doc.custom_account_paid_to_1}"
    
    # revert the main account GL entry to original amount but keep the same against format
    if doc.payment_type == "Receive":
        frappe.db.sql("""
            UPDATE `tabGL Entry` 
            SET debit = %s, 
                debit_in_account_currency = %s,
                debit_in_transaction_currency = %s,
                against = %s,
                modified = NOW(),
                modified_by = %s
            WHERE voucher_no = %s 
            AND account = %s
            AND voucher_type = %s
            AND is_cancelled = 1
            ORDER BY debit DESC
            LIMIT 1
        """, (
            total_amount, total_amount, total_amount, against_accounts,
            frappe.session.user, doc.name, main_account, doc.doctype
        ))
    else:
        frappe.db.sql("""
            UPDATE `tabGL Entry` 
            SET credit = %s, 
                credit_in_account_currency = %s,
                credit_in_transaction_currency = %s,
                against = %s,
                modified = NOW(),
                modified_by = %s
            WHERE voucher_no = %s 
            AND account = %s
            AND voucher_type = %s
            AND is_cancelled = 1
            ORDER BY debit DESC
            LIMIT 1
        """, (
            total_amount, total_amount, total_amount, against_accounts,
            frappe.session.user, doc.name, main_account, doc.doctype
        ))
