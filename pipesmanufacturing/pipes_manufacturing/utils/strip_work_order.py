import frappe
import json
from frappe.utils import flt, get_datetime, getdate, add_days, date_diff, nowdate, today
from frappe.model.document import Document

@frappe.whitelist()
def update_calculations(doc):
    frappe.msgprint("Hello World")
    frappe.msgprint('{0}'.format(doc))