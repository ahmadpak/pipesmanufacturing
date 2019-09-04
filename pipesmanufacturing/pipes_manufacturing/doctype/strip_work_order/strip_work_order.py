# -*- coding: utf-8 -*-
# Copyright (c) 2019, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import math
from frappe import msgprint, _
from frappe.utils import flt, new_line_sep, get_datetime, getdate, date_diff, cint, nowdate
from erpnext.stock.utils import get_bin
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe.model.document import Document

class StripWorkOrder(Document):
	def validate(self):
		update_calculations(self)

	def on_submit(self):
		status = "Not Started"
		self.db_set("status",status)
		self.update_bin_batch()
	
	def on_cancel(self):
		updated_stock_on_cancel(self)

	def update_bin_batch(self):
		coil_bin = get_bin(self.required_item,self.s_warehouse)
		if self.batch_qty != coil_bin.projected_qty:
			frappe.throw('Batch available quantity is: {0} kg'.format(coil_bin.projected_qty))

		update_projected_qty(self.required_item,self.s_warehouse,None,None,self.allocate_quantity)
		update_projected_qty(self.required_item,self.wip_warehouse,self.allocate_quantity,None,self.allocate_quantity)
		
		batch = frappe.get_doc('Batch',self.batch_no)
		s_batch_qty = get_batch_qty(self.batch_no,self.s_warehouse)
		s_reserved_qty = coil_bin.reserved_qty_for_production
		available_batch_qty = s_batch_qty - s_reserved_qty
		if available_batch_qty == 0:
			batch.db_set('batch_stock_status','Empty')	

def update_projected_qty(item_code,warehouse,indented_qty,planned_qty,reserved_qty_for_production):
	swo_bin = get_bin(item_code,warehouse)
	# Dealing with None variables
	if indented_qty == None:
		if swo_bin.indented_qty == None:
			swo_bin.db_set("indented_qty",0)
	else:
		if swo_bin.indented_qty == None:
			swo_bin.db_set("indented_qty",0)
		indented_qty += round(swo_bin.indented_qty)
		swo_bin.db_set("indented_qty",round(indented_qty))

	if planned_qty == None:
		if swo_bin.planned_qty == None:
			swo_bin.db_set("planned_qty",0)
	else:
		if swo_bin.planned_qty == None:
			swo_bin.db_set("planned_qty",0)
		planned_qty += round(swo_bin.planned_qty)
		swo_bin.db_set("planned_qty",round(planned_qty))
	
	if reserved_qty_for_production == None:
		if swo_bin.reserved_qty_for_production == None:
			swo_bin.db_set("reserved_qty_for_production",0)
	else:
		if swo_bin.reserved_qty_for_production == None:
			swo_bin.db_set("reserved_qty_for_production",0)
		reserved_qty_for_production += round(swo_bin.reserved_qty_for_production)
		swo_bin.db_set("reserved_qty_for_production",round(reserved_qty_for_production))
	
	new_projected_qty = swo_bin.actual_qty+						\
						swo_bin.ordered_qty+					\
						swo_bin.indented_qty+					\
						swo_bin.planned_qty-					\
						swo_bin.reserved_qty-					\
						swo_bin.reserved_qty_for_production
	swo_bin.db_set("projected_qty",new_projected_qty)

def update_calculations(self):
	if self.allocate_quantity!= None and self.allocate_quantity>0:
		i = show_error = tmp_total_strips_weight = 0
		for item in self.production_item:
			if (item.pipe_item_code):
				if item.qty==None or item.qty<=0:
					frappe.msgprint(" Row {1}: Quanity of {0} must be greater than zero".format(item.pipe_item_code,i+1))
					show_error = 1
				else:
					if show_error!=1:
						item.strip_weight = round((item.strip_width/self.coil_width)*self.allocate_quantity)
						item.total_strip_weight = round(item.strip_weight*item.qty)
						tmp_total_strips_weight +=item.total_strip_weight
		if show_error==1:
			frappe.throw("Please correct!")
		self.total_strips_weight = tmp_total_strips_weight
		self.coil_side_cutting = round(self.allocate_quantity - self.total_strips_weight)
		self.scrap_percentage = round((self.coil_side_cutting/self.allocate_quantity)*100,2)
	else:
		frappe.throw("Allocated quantity must be greater than zero")

def updated_stock_on_cancel(self):
	if self.status == 'Started' or self.status == 'Not Started':
		update_projected_qty(self.required_item,self.s_warehouse,None,None,-(self.allocate_quantity))
		update_projected_qty(self.required_item,self.wip_warehouse,-(self.allocate_quantity),None,-(self.allocate_quantity))
		batch = frappe.get_doc('Batch',self.batch_no)
		batch.db_set('batch_stock_status','Available')

	if self.status == 'In Process':
		update_projected_qty(self.required_item,self.wip_warehouse,None, None, -(self.allocate_quantity))
		update_projected_qty('Coil Side Cutting',self.scrap_warehouse,None,-(self.coil_side_cutting),None)
		for item in self.production_item:
				update_projected_qty(item.strip_item_code,self.t_warehouse,None,-(item.total_strip_weight),None)
		batch = frappe.get_doc('Batch',self.batch_no)
		batch.db_set('batch_stock_status','Available')

	if self.status == 'Stopped':
		frappe.throw("Cannot Cancel a stopped work order")

@frappe.whitelist()
def batch_qty(batch_no,s_warehouse,required_item):
	s_batch_qty = get_batch_qty(batch_no,s_warehouse)
	coil_bin = get_bin(required_item,s_warehouse)
	s_reserved_qty = coil_bin.reserved_qty_for_production
	available_batch_qty = s_batch_qty - s_reserved_qty
	return available_batch_qty

@frappe.whitelist()
def start(strip_work_order):
	swo = frappe.get_doc("Strip Work Order",strip_work_order)
	status = "Started"
	swo.db_set("status",status)
	swo.db_set("actual_start_date", get_datetime())

@frappe.whitelist()
def stop_unstop(strip_work_order,status):
	swo = frappe.get_doc("Strip Work Order",strip_work_order)
	if status == "Stopped":
		swo.db_set("status",status)
	else:
		if swo.transferred_quantity == 0:
			status = "Started"
			swo.db_set("actual_start_date", get_datetime())
		elif swo.total_strips_weight == 0:
			status = 'In Process'
		else:
			status = "Completed"
			swo.db_set("actual_end_date", get_datetime())

		swo.db_set("status",status)
	#swo.reload()
	
@frappe.whitelist()
def update_stock(strip_work_order,status):
	if status == "Material Transferred":
		swo = frappe.get_doc('Strip Work Order',strip_work_order)
		mt = frappe.new_doc('Stock Entry')
		mt.update({
			'stock_entry_type': 'Material Transfer for Manufacture',
			'strip_work_order': strip_work_order,
			'from_warehouse': swo.s_warehouse,
			'to_warehouse': swo.wip_warehouse
		})
		mt.append('items',{
			's_warehouse': swo.s_warehouse,
			't_warehouse': swo.wip_warehouse,
			'item_code': swo.required_item,
			'qty': swo.allocate_quantity,
			'batch_no': swo.batch_no
		})
		mt.save()
		mt.submit()
		update_projected_qty(swo.required_item,swo.s_warehouse,None,None,-(swo.allocate_quantity))
		update_projected_qty(swo.required_item,swo.wip_warehouse,-(swo.allocate_quantity),None,None)
		update_projected_qty('Coil Side Cutting',swo.scrap_warehouse,None,swo.coil_side_cutting,None)
		for item in swo.production_item:
				update_projected_qty(item.strip_item_code,swo.t_warehouse,None,item.total_strip_weight,None)
		
		swo.db_set('transferred_quantity',swo.allocate_quantity)
		swo.db_set('status','In Process')

	elif status == 'Material Manufacture':
		swo = frappe.get_doc('Strip Work Order',strip_work_order)
		mf = frappe.new_doc('Stock Entry')
		mf.update({
			'stock_entry_type': 'Manufacture',
			'strip_work_order': strip_work_order
		})

		#Entering Item for Coil
		mf.append('items',{
					's_warehouse': swo.wip_warehouse,
					'item_code': swo.required_item,
					'qty': swo.allocate_quantity,
					'batch_no': swo.batch_no
				})
		mf.save()
		temp_base_rate = round(mf.total_outgoing_value/swo.allocate_quantity,2)
		update_projected_qty(swo.required_item,swo.wip_warehouse,None,None,-(swo.allocate_quantity))

		for item in swo.production_item:
			for i in range(int(item.qty)):
				mf.append('items',{
					't_warehouse': swo.t_warehouse,
					'item_code': item.strip_item_code,
					'qty': item.strip_weight,
					'basic_rate': temp_base_rate
				})

		mf.append('items',{
					't_warehouse': swo.scrap_warehouse,
					'item_code': 'Coil Side Cutting',
					'qty': swo.coil_side_cutting,
					'basic_rate': temp_base_rate
				})	
		mf.save()
		mf.submit()

		update_projected_qty('Coil Side Cutting',swo.scrap_warehouse,None,-(swo.coil_side_cutting),None)
		for item in swo.production_item:
				update_projected_qty(item.strip_item_code,swo.t_warehouse,None,-(item.total_strip_weight),None)

		swo.db_set('status','Completed')
	