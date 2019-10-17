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


def verify_items(self,frm):
        item_cmp1 = None
        item_cmp2 = None
        throw_error = 0
        for i in range(len(self.items)):
            item_cmp1 = self.items[len(self.items)-i-1].item_code
            for j in range(len(self.items)):
                
                if j < len(self.items)-i-1:
                    item_cmp2 = self.items[j].item_code
                    if item_cmp1 == item_cmp2:
                        #frappe.msgprint('{0} is alreaded added in row {1}'.format(item_cmp1,j+1))
                        throw_error = 1
        has_non_pipe = 0
        has_pipe = 0
        for i in self.items:
            if 'Pipe-MS' in str(i.item_code):
                has_pipe = 1
            else:
                has_non_pipe = 1
        if has_pipe == has_non_pipe == 1:
            frappe.throw('Cannot add Pipe and Non-Pipe items together please correct!')
        if throw_error == 1:
            frappe.throw('Cannot add an item multiple times please correct!')