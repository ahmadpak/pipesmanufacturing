from __future__ import unicode_literals
import frappe
import math
from frappe import msgprint, _
from frappe.utils import flt, get_datetime
from frappe.model.document import Document
from erpnext.stock.utils import get_bin
from erpnext.stock.doctype.batch.batch import get_batch_qty

class PipesWorkOrder(Document):
    def validate(self):
        pass

    def on_submit(self):
        self.check_warehouses()
        self.update_material_request('on_submit')
    
    def on_cancel(self):
        self.update_material_request('on_cancel')

    def on_trash(self):
        self.update_material_request('on_trash')
    
    def check_warehouses(self):
        throw_error = 0
        if not self.s_warehouse:
            throw_error = 1
        elif not self.wip_warehouse and self.skip_transfer == 0:
            throw_error = 1
        elif not self.t_warehouse:
            throw_error = 1
        elif not self.scrap_warehouse:
            throw_error = 1
        elif not self.a_quality_pipe_warehouse:
            throw_error = 1
        elif not self.b_quality_pipe_warehouse:
            throw_error = 1    
        elif not self.required_items:
            throw_error = 1
        if throw_error == 1:
            frappe.throw(_("Please enter the missing values!"))

    def update_material_request(self,action):
        if action == 'on_submit':
            if self.req_qty>self.qty:
                frappe.throw('Quantity to manufacture must be equal or greater than requested quantity, please add more raw material!')
            
            # Updating pipe work order field on material request
            mr = frappe.get_doc('Material Request', self.material_request)
            if (self.amended_from == mr.pipes_work_order):
                mr.db_set('pipes_work_order',self.name)
            elif mr.pipes_work_order != mr.pipes_work_order:
                frappe.throw("Pipes work order# {0} is already made for Material Request# {1}".format(mr.pipes_work_order,mr.name))
            #updating item ordered quantities
            total_qty_tmp = total_ordered_tmp = 0
            for item in mr.items:
                if (item.item_code == self.production_item):
                    item.db_set('ordered_qty',self.req_qty)
                    total_ordered_tmp += self.req_qty
                    total_qty_tmp += item.qty
                else:
                    total_ordered_tmp += item.ordered_qty
                    total_qty_tmp += item.qty

            #Updating Material Request status
            mr.db_set('per_ordered',round((total_ordered_tmp/total_qty_tmp)*100,2))
            if ((total_ordered_tmp/total_qty_tmp)*100)<100:
                mr.db_set('status','Partially Ordered')
            else:
                mr.db_set('status','Ordered')

            #Updating Batch
            strip_item_code = None
            for item in self.required_items:
                if strip_item_code == None:
                    strip_item_code = item.item_code
                batch = frappe.get_doc('Batch',item.batch_no)
                batch.db_set('batch_stock_status','Consumed')
                batch.db_set('allocated_quantity',item.batch_qty)
                batch.db_set('pipes_work_order',self.name)

            # Updating bin for Pipe
            update_projected_qty(self.production_item,self.t_warehouse,-(self.req_qty),self.qty,None)     
            
            #Updating bin for Strip   
            update_projected_qty(strip_item_code,self.s_warehouse,None,None,self.total_required_material)
            update_projected_qty(strip_item_code,self.wip_warehouse,self.total_required_material,None,self.total_required_material)
            
            self.db_set('status','Not Started')                

        elif action == 'on_cancel':
            mr = frappe.get_doc('Material Request', self.material_request)
            mr.db_set('pipes_work_order',None)
        elif action == 'on_trash':
            mr = frappe.get_doc('Material Request', self.material_request)
            mr.db_set('pipes_work_order',None)

def update_projected_qty(item_code,warehouse,indented_qty,planned_qty,reserved_qty_for_production):
    pwo_bin = get_bin(item_code,warehouse)
    # Dealing with None variables
    if indented_qty == None:
        if pwo_bin.indented_qty == None:
            pwo_bin.db_set("indented_qty",0)
    else:
        if pwo_bin.indented_qty == None:
            pwo_bin.db_set("indented_qty",0)
        indented_qty += round(pwo_bin.indented_qty,2)
        pwo_bin.db_set("indented_qty",round(indented_qty,2))

    if planned_qty == None:
        if pwo_bin.planned_qty == None:
            pwo_bin.db_set("planned_qty",0)
    else:
        if pwo_bin.planned_qty == None:
            pwo_bin.db_set("planned_qty",0)
        planned_qty += round(pwo_bin.planned_qty,2)
        pwo_bin.db_set("planned_qty",round(planned_qty,2))
    
    if reserved_qty_for_production == None:
        if pwo_bin.reserved_qty_for_production == None:
            pwo_bin.db_set("reserved_qty_for_production",0)
    else:
        if pwo_bin.reserved_qty_for_production == None:
            pwo_bin.db_set("reserved_qty_for_production",0)
        reserved_qty_for_production += round(pwo_bin.reserved_qty_for_production,2)
        pwo_bin.db_set("reserved_qty_for_production",round(reserved_qty_for_production,2))
    
    new_projected_qty = pwo_bin.actual_qty+                        \
                        pwo_bin.ordered_qty+                    \
                        pwo_bin.indented_qty+                    \
                        pwo_bin.planned_qty-                    \
                        pwo_bin.reserved_qty-                    \
                        pwo_bin.reserved_qty_for_production
    pwo_bin.db_set("projected_qty",new_projected_qty)

@frappe.whitelist()
def set_status(pipes_work_order):
    pwo = frappe.get_doc('Pipes Work Order',pipes_work_order)
    total_scrap = pwo.pipe_jala_bora + pwo.phakra_pipe + pwo.bari_end_cut
    total_weight_produced = pwo.total_weight + total_scrap
    total_weight_processed = round((pwo.no_of_a_quality_pipes + pwo.no_of_b_quality_pipes)*pwo.weight,2) + total_scrap

    if pwo.mtf_manufacturing == None or pwo.mtf_manufacturing == 0:
        pwo.db_set('status','Started')
    elif pwo.mtf_manufacturing<pwo.total_required_material and (pwo.status == 'Started' or pwo.status == 'Stopped'):
        pwo.db_set('status','Material Partially Transfered')
    elif total_weight_produced != pwo.total_required_material and pwo.mtf_manufacturing == pwo.total_required_material and (pwo.status == 'Started' or pwo.status == 'Material Partially Transfered' or pwo.status == 'Stopped'):
        pwo.db_set('status', 'In Process')
    elif total_weight_processed != pwo.total_required_material and total_weight_produced == pwo.total_required_material and (pwo.status == 'In Process' or pwo.status == 'Stopped'):
        pwo.db_set('status', 'Quality Inspection')
    elif total_weight_processed == pwo.total_required_material and (pwo.status == 'In Process' or pwo.status == 'Quality Inspection' or pwo.status == 'Stopped'):
        pwo.db_set('status', 'Completed')
        i = pwo.qty-pwo.produced_qty
        update_projected_qty(pwo.production_item,pwo.t_warehouse,None,-i,None)


@frappe.whitelist()
def get_item_attributes(item_code, variant):
    #Extracting Thickness and Width
    item = frappe.get_doc('Item', item_code)
    thickness_temp = width_temp = 0
    if str(item.variant_of) in [variant]:
        for item_attributes in item.attributes:
            attribute_name = str(item_attributes.attribute)
            if 'Thickness' in attribute_name:
                thickness_temp = float(item_attributes.attribute_value)
            elif 'Width' in attribute_name:
                width_temp = float(item_attributes.attribute_value)
        return{'thickness': thickness_temp, 'width': width_temp}

@frappe.whitelist()
def batch_qty(batch_no,s_warehouse):
    batch_doc = frappe.get_doc('Batch',batch_no)
    required_item = batch_doc.item
    s_batch_qty = get_batch_qty(batch_no,s_warehouse)
    strip_bin = get_bin(required_item,s_warehouse)
    #s_reserved_qty = strip_bin.reserved_qty_for_production
    s_reserved_qty = batch_doc.allocated_quantity
    available_batch_qty = s_batch_qty - s_reserved_qty
    return {'available_qty':available_batch_qty, 'required_item':required_item}

@frappe.whitelist()
def stop_unstop(pipes_work_order,status):
    pwo = frappe.get_doc('Pipes Work Order',pipes_work_order)
    if status == 'start':
        pwo.db_set('status','Started')
    elif status == 'stop':
        pwo.db_set('status','Stopped')
    elif status == 'resume':
        set_status(pipes_work_order)



@frappe.whitelist()
def material_transfer(pipes_work_order,selected_batch,status):    
    pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
    selected_batch = selected_batch.split(',')
    mtf_manufacturing_tmp = pwo.mtf_manufacturing
    strip_transferred = 0
    strip_item_code = None
    mt = frappe.new_doc("Stock Entry")
    mt.update({
        "stock_entry_type": "Material Transfer for Manufacture",
        "pipes_work_order": pipes_work_order,
        "from_warehouse": pwo.s_warehouse,
        "to_warehouse": pwo.wip_warehouse
    })

    for x in selected_batch:
        if x!='':
            for item in pwo.required_items:
                if item.batch_no == x:
                    if strip_item_code == None:
                        strip_item_code = item.item_code
                    item.db_set('status','Transferred')
                    mt.append("items",{
                        "s_warehouse": pwo.s_warehouse,
                        "t_warehouse": pwo.wip_warehouse,
                        "item_code": item.item_code,
                        "qty": item.batch_qty,
                        "batch_no": item.batch_no
                    })

                    mtf_manufacturing_tmp +=item.batch_qty
                    strip_transferred += item.batch_qty

    mt.save()
    mt.submit()

    #Updating projected quantity
    pwo.db_set('mtf_manufacturing',mtf_manufacturing_tmp)
    update_projected_qty(strip_item_code,pwo.s_warehouse,None,None,-float(strip_transferred))
    update_projected_qty(strip_item_code,pwo.wip_warehouse,-float(strip_transferred),None,None)
    set_status(pipes_work_order)

@frappe.whitelist()
def update_mtf_manufacturing(pipes_work_order):
    pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
    mtf_manufacturing_tmp = 0
    for item in pwo.required_items:
        if item.status != "Not Transferred":
            mtf_manufacturing_tmp += item.batch_qty
    pwo.db_set("mtf_manufacturing", mtf_manufacturing_tmp)
    set_status(pipes_work_order)

@frappe.whitelist()
def pipe_manufacture(pipes_work_order,pipe_qty,status):
    pipe_qty = int(pipe_qty)
    pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
    weight_to_produce = round(pipe_qty*pwo.weight,2)                #Total weight of the pipes to be produced
    total_strip_used = weight_to_produce

    #Creating new Stock Entry
    mf = frappe.new_doc('Stock Entry')
    mf.update({
        'stock_entry_type': 'Manufacture',
        'pipes_work_order': pipes_work_order
    })
    strip_item_code = ''
    #Looping through batches to check if batch qty is enough
    for item in pwo.required_items:
        if weight_to_produce!=0:
            if strip_item_code == '':
                strip_item_code = item.item_code 
            if item.consumed_qty!=item.batch_qty and item.status == 'Transferred':
                batch_available_quantity = round((item.batch_qty - item.consumed_qty),2)
                if weight_to_produce >= batch_available_quantity:
                    mf.append("items",{
                            "s_warehouse": pwo.wip_warehouse,
                            "item_code": item.item_code,
                            "qty": batch_available_quantity,
                            "batch_no": item.batch_no    
                        })
                    new_consumed_qty = item.consumed_qty + batch_available_quantity
                    item.db_set("consumed_qty",new_consumed_qty)
                    if new_consumed_qty == item.batch_qty:
                        item.db_set('status','Consumed')
                    weight_to_produce -= batch_available_quantity
                else:
                    mf.append("items",{
                            "s_warehouse": pwo.wip_warehouse,
                            "item_code": item.item_code,
                            "qty": weight_to_produce,
                            "batch_no": item.batch_no    
                        })
                    new_consumed_qty = item.consumed_qty + weight_to_produce
                    item.db_set("consumed_qty",new_consumed_qty)
                    if new_consumed_qty == item.batch_qty:
                        item.db_set('status','Consumed')
                    weight_to_produce -= weight_to_produce
        else:
            break
    mf.save()

    tmp_basic_rate = round(mf.total_outgoing_value/pipe_qty,2)
    mf.append("items",{
        "t_warehouse": pwo.t_warehouse,
        "item_code": pwo.production_item,
        "qty": pipe_qty,
        "basic_rate": tmp_basic_rate
    })
    mf.save()
    mf.submit()

    update_projected_qty(strip_item_code,pwo.wip_warehouse,None,None,-total_strip_used) 
    update_projected_qty(pwo.production_item,pwo.t_warehouse,None,-pipe_qty,None)

    #Updating Pipes Work Order produced quantity
    total_produced_quantity = pipe_qty + pwo.produced_qty
    pwo.db_set('produced_qty', total_produced_quantity)
    total_weight = round(total_produced_quantity*pwo.weight,2)
    total_length = round(total_produced_quantity*pwo.length,2)
    pwo.db_set('total_weight',total_weight)
    pwo.db_set('total_length',total_length)

    #Updating Material Request
    mr_per_ordered = 0
    mr_received_qty = 0
    mr_total_qty = 0
    mr = frappe.get_doc("Material Request",pwo.material_request)

    #Looping through Material Request items to update ordered and received quanities
    for item in mr.items:
        if item.item_code == pwo.production_item and item.ordered_qty!=item.received_qty and item.qty==pwo.req_qty:
            new_received_qty = item.received_qty + pipe_qty
            item.db_set('received_qty',new_received_qty)
            mr_per_ordered += item.ordered_qty
            mr_received_qty +=new_received_qty
            mr_total_qty += item.qty
        else:
            mr_per_ordered += item.ordered_qty
            mr_received_qty +=item.received_qty
            mr_total_qty += item.qty
    
    percentage_ordered = round((mr_per_ordered)*100/mr_total_qty,2)
    percentage_received = round((mr_received_qty)*100/mr_total_qty,2)
    mr.db_set("per_ordered", percentage_ordered)
    mr.db_set("per_received", percentage_received)

    if percentage_ordered < 100:
        mr.db_set("status","Partially Ordered")
    elif percentage_ordered==100 and percentage_received < 100:
        mr.db_set("status","Ordered")
    else:
        mr.db_set("status","Manufactured")
            
    set_status(pipes_work_order)

@frappe.whitelist()
def scrap_trasnfer(pipes_work_order,pipe_jala_bora,phakra_pipe,bari_end_cut):
    pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
    pipe_jala_bora = float(pipe_jala_bora)
    phakra_pipe = float(phakra_pipe)
    bari_end_cut = float(bari_end_cut)
    total_scrap = pipe_jala_bora + phakra_pipe + bari_end_cut
    total_stirp_used = total_scrap
    #Creating new stock entry
    mf = frappe.new_doc("Stock Entry")
    mf.update({
        "stock_entry_type": "Manufacture",
        "pipes_work_order": pipes_work_order
    })
    strip_item_code = ''
    #Looping through batches to check if batch qty is enough
    for item in pwo.required_items:
        if total_scrap!=0:
            if strip_item_code == '':
                strip_item_code = item.item_code 
            if item.consumed_qty!=item.batch_qty and item.status == 'Transferred':
                batch_available_quantity = round((item.batch_qty - item.consumed_qty),2)
                if total_scrap >= batch_available_quantity:
                    mf.append("items",{
                            "s_warehouse": pwo.wip_warehouse,
                            "item_code": item.item_code,
                            "qty": batch_available_quantity,
                            "batch_no": item.batch_no    
                        })
                    new_consumed_qty = item.consumed_qty + batch_available_quantity
                    item.db_set("consumed_qty",new_consumed_qty)
                    if new_consumed_qty == item.batch_qty:
                        item.db_set('status','Consumed')
                    total_scrap -= batch_available_quantity
                else:
                    mf.append("items",{
                            "s_warehouse": pwo.wip_warehouse,
                            "item_code": item.item_code,
                            "qty": total_scrap,
                            "batch_no": item.batch_no    
                        })
                    new_consumed_qty = item.consumed_qty + total_scrap
                    item.db_set("consumed_qty",new_consumed_qty)
                    if new_consumed_qty == item.batch_qty:
                        item.db_set('status','Consumed')
                    total_scrap -= total_scrap
        else:
            break

    mf.save()
    basic_rate = round(mf.total_outgoing_value/total_stirp_used,2)
    if pipe_jala_bora!=0:
        mf.append("items",{
            "t_warehouse": pwo.scrap_warehouse,
            "item_code": "Pipe Jala Bora",
            "qty": pipe_jala_bora,
            "basic_rate": basic_rate
        })
        pipe_jala_bora += pwo.pipe_jala_bora
        pwo.db_set("pipe_jala_bora",pipe_jala_bora)
    if phakra_pipe!=0:
        mf.append("items",{
            "t_warehouse": pwo.scrap_warehouse,
            "item_code": "Phakra Pipe",
            "qty": phakra_pipe,
            "basic_rate": basic_rate
        })
        phakra_pipe += pwo.phakra_pipe
        pwo.db_set("phakra_pipe",phakra_pipe)

    if bari_end_cut!=0:
        mf.append("items",{
            "t_warehouse": pwo.scrap_warehouse,
            "item_code": "Bari End Cut",
            "qty": bari_end_cut,
            "basic_rate": basic_rate
        })
        bari_end_cut += pwo.bari_end_cut
        pwo.db_set("bari_end_cut",bari_end_cut)
    mf.save()
    mf.submit()
    update_projected_qty(strip_item_code,pwo.wip_warehouse,None,None,-total_stirp_used)
    set_status(pipes_work_order)


@frappe.whitelist()
def quality_inspection(pipes_work_order,pipe_a_qty,pipe_b_qty):
    pipe_a_qty = int(pipe_a_qty)
    pipe_b_qty = int(pipe_b_qty)
    pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
    pipe_a = pwo.no_of_a_quality_pipes + pipe_a_qty
    pipe_b = pwo.no_of_b_quality_pipes + pipe_b_qty
    pwo.db_set("no_of_a_quality_pipes",pipe_a)
    pwo.db_set("no_of_b_quality_pipes",pipe_b)
    
    #frappe.throw("break")
    #Creating new Stock Entry
    mt = frappe.new_doc("Stock Entry")
    mt.update({
        "stock_entry_type": "Material Transfer",
        "from_warehouse": pwo.t_warehouse,
        "pipes_work_order": pipes_work_order
    })

    # Inserting A quality items
    if pipe_a_qty!= 0:
        mt.append("items",{
            "s_warehouse": pwo.t_warehouse,
            "t_warehouse": pwo.a_quality_pipe_warehouse,
            "item_code": pwo.production_item,
            "qty": pipe_a_qty
        })

    # Inserting B quality items
    if pipe_b_qty!= 0:
        mt.append("items",{
            "s_warehouse": pwo.t_warehouse,
            "t_warehouse": pwo.b_quality_pipe_warehouse,
            "item_code": pwo.production_item,
            "qty": pipe_b_qty
        })

    mt.save()
    mt.submit()
    set_status(pipes_work_order)