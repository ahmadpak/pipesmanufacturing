import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.batch.batch import get_batch_qty
def update_batch_stock_status(self, cdt):
    if self.doctype == "Purchase Receipt":
        for item in self.items:
            if "Strip-MS" in str(item.item_code):
                msg = get_batch_qty(item.batch_no)
                total_batch_qty = 0
                for x in msg:
                    total_batch_qty +=int(x.qty)
                if msg:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Available"
                    batch_msg.save() 
                else:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Empty"
                    batch_msg.save()
                
    elif self.doctype == "Delivery Note":  
        for item in self.items:
            if "Strip-MS" in str(item.item_code):
                msg = get_batch_qty(item.batch_no)
                total_batch_qty = 0
                for x in msg:
                    total_batch_qty +=int(x.qty)
                if total_batch_qty>0:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Available"
                    batch_msg.save() 
                else:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Empty"
                    batch_msg.save()
                
    else:
        for item in self.items:
            if "Strip-MS" in str(item.item_code):
                msg = get_batch_qty(item.batch_no)
                total_batch_qty = 0
                for x in msg:
                    total_batch_qty +=int(x.qty)
                if total_batch_qty>0:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Available"
                    batch_msg.save() 
                else:
                    batch_msg = frappe.get_doc("Batch",item.batch_no)
                    batch_msg.batch_stock_status = "Empty"
                    batch_msg.save()
                


