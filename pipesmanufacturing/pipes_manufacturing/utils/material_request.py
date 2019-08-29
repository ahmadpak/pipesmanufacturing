from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def raise_pipes_work_orders(material_request):
    mr= frappe.get_doc("Material Request", material_request)
    pipes_orders = []
    default_wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")
    for d in mr.items:
        if (d.qty - d.ordered_qty) >0:
            pipes_order = frappe.new_doc("Pipes Work Order")
            pipes_order.update({
                "production_item": d.item_code,
                "wip_warehouse": default_wip_warehouse,
                "t_warehouse": d.warehouse,
                "planned_start_date": mr.transaction_date,
                "planned_end_date": d.schedule_date,
                "material_request": mr.name,
                "req_qty": d.qty - d.ordered_qty,
            })
            pipes_order.save()
            mr.db_set("pipes_work_order",pipes_order.name)
            #pipes_orders.append(pipes_order.name)
            frappe.msgprint("Pipes Work Order# " + pipes_order.name + " created")
