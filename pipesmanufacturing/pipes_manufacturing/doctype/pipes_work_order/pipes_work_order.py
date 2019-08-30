# -*- coding: utf-8 -*-
# Copyright (c) 2019, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import math
from frappe import msgprint, _
from frappe.utils import flt, new_line_sep, get_datetime, getdate, date_diff, cint, nowdate
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from erpnext.stock.doctype.stock_entry.stock_entry import get_additional_costs
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations
from erpnext.stock.stock_balance import get_planned_qty, get_indented_qty
from frappe.utils.csvutils import getlink
from erpnext.stock.utils import get_bin, validate_warehouse_company, get_latest_stock_qty
from erpnext.utilities.transaction_base import validate_uom_is_integer


class PipesWorkOrder(Document):
	def validate(self):
		self.status = self.get_status() #Updating status
		self.check_mr_pwo()				#Checking if MR has different PWO already
	
	def on_submit(self):
		self.check_warehouses()			#Checking Warehouses section
		self.check_s_warehouse()		#Checking Required Items warehouse
		self.pwo_update_bin()			#Updating Item Bin values
		self.update_material_request()	#Updating Material Request status
		
		
		
		
	def on_cancel(self):
		self.pwo_update_bin()			#Updating Item Bin values
		self.status = self.get_status()	#Updating status
		self.update_material_request()  #Updating Material Request status
		
	
	def on_trash(self):
		if self.material_request:
			mr = frappe.get_doc("Material Request", self.material_request)
			mr.db_set("pipes_work_order",None)
			mr.reload()
			self.material_request = None
			self.reload()

	def update_status(self, status = None):
		if not status:
			status = self.get_status(status)
		if status != self.status:
			self.db_set("status", status)
		return status
	
	def get_status(self, status = None):
		if not status:
			status = self.status
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if status != 'Stopped':
				if self.produced_qty == 0 and self.mtf_manufacturing == 0:
					status = "Not Started"
				elif self.mtf_manufacturing >0 and self.mtf_manufacturing!=self.total_required_material:
					status = "Material Partially Transfered"
				elif self.mtf_manufacturing == self.total_required_material and round(self.produced_qty,2)!=round(self.qty,2):
					status = "In Process"
				elif round(self.produced_qty,2)==round(self.qty,2) :
					status = "Completed"
		elif self.docstatus == 2:
			status = "Cancelled"
				
		return status

	def pwo_update_bin(self):
		if self.docstatus == 1:
			#Updating Pipe Item Bin
			if round(self.qty,2)!= 0 and self.t_warehouse:
				init_bin(self.production_item,self.t_warehouse)
				pipe_bin = get_bin(self.production_item,self.t_warehouse)
				
				new_indented_qty = 0
				new_indented_qty = pipe_bin.indented_qty - self.req_qty

				new_planned_qty = 0
				new_planned_qty = pipe_bin.planned_qty + round(self.qty,2)

				#Updating projected quantity
				update_projected_qty(
									self.production_item,
									self.t_warehouse,
									new_indented_qty,
									new_planned_qty,
									None)
				
			#Updating Strip Item(s) Bin
			if self.required_items:
				#Looping through required items				
				for d in self.required_items:
					new_strip_reserved_qty_for_production = 0					#Variable for new reserved qty
					new_strip_indented_qty = 0
					wip_reserved_qty = 0									#Variable for new indented qty
					init_bin(d.item_code,d.batch_warehouse)						#Checking if any value is "None" in bin
					strip_bin_store = get_bin(d.item_code,d.batch_warehouse)	#Declaring bin object for source warehouse
					init_bin(d.item_code,self.wip_warehouse)					#Checking if any value is "None" in bin
					strip_bin_wip = get_bin(d.item_code,self.wip_warehouse)		#Declaring bin object for wip warehouse
					
					if d.batch_qty!=0:
						#For Source Warehouse
						new_strip_reserved_qty_for_production += strip_bin_store.reserved_qty_for_production + d.batch_qty 
	
						#For WIP Warehouse
						if self.skip_transfer == 0:
							new_strip_indented_qty += strip_bin_wip.indented_qty + d.batch_qty
							wip_reserved_qty += strip_bin_wip.reserved_qty_for_production + d.batch_qty
					#Updating projected quantity
					update_projected_qty(
										d.item_code,
										d.batch_warehouse,
										None,
										None,
										new_strip_reserved_qty_for_production
					)
					update_projected_qty(
										d.item_code,
										self.wip_warehouse,
										new_strip_indented_qty,
										strip_bin_wip.planned_qty,
										wip_reserved_qty
					)

	
		else:
			#Updating Pipe Item Bin on Cancel
			if round(self.qty,2)!= 0 and self.t_warehouse:
				pipe_bin = get_bin(self.production_item,self.t_warehouse)
				
				new_indented_qty = 0
				new_indented_qty = pipe_bin.indented_qty + self.req_qty

				new_planned_qty = 0
				new_planned_qty = pipe_bin.planned_qty - round(self.qty,2)

				#Updating projected quantity
				update_projected_qty(
									self.production_item,
									self.t_warehouse,
									new_indented_qty,
									new_planned_qty,
									None)

			#Updating Strip Item(s) Bin
			if self.required_items:
				
				for d in self.required_items:
					new_strip_reserved_qty_for_production = 0					#Variable for new reserved qty
					new_strip_indented_qty = 0									#Variable for new indented qty
					strip_bin_store = get_bin(d.item_code,d.batch_warehouse)	#Declaring bin object for source warehouse
					strip_bin_wip = get_bin(d.item_code,self.wip_warehouse)		#Declaring bin object for wip warehouse
					if d.batch_qty!=0:
						new_strip_reserved_qty_for_production += strip_bin_store.reserved_qty_for_production - d.batch_qty

						#For WIP Warehouse
						if self.skip_transfer == 0:
							new_strip_indented_qty += strip_bin_wip.indented_qty - d.batch_qty
					
					#Updating projected quantity
					update_projected_qty(
										d.item_code,
										d.batch_warehouse,
										None,
										None,
										new_strip_reserved_qty_for_production
					)
					update_projected_qty(
										d.item_code,
										self.wip_warehouse,
										new_strip_indented_qty,
										None,
										None
					)
			
	# Updating material request values
	def update_material_request(self):
		if self.material_request:
			mr = frappe.get_doc("Material Request", self.material_request)
			if mr.pipes_work_order == None:
				mr.db_set("pipes_work_order",self.name)
			elif mr.pipes_work_order != self.name:
				frappe.throw("Pipes work order# {0} is already made for Material Request# {1}".format(mr.pipes_work_order,mr.name))
		
		if self.qty < self.req_qty:
			frappe.msgprint(_("Qty to Manucture must be greater than Required Quantity"))
			frappe.throw(_("Please add more required items"))
		
		if self.material_request and self.status=="Not Started":
			throw_error = 0
			for item in self.required_items:
				batch = frappe.get_doc("Batch",item.batch_no)
				if batch.pipes_work_order == None:
					batch.db_set("pipes_work_order",self.name)
				else:
					frappe.msgprint("Batch is already in use for: {0}".format(batch.pipes_work_order))
					throw_error = 1
			if throw_error == 1:
				frappe.throw("Please use different batch")
			mr = frappe.get_doc("Material Request", self.material_request)
			mr_per_ordered = 0
			mr_req_qty = 0
			mr_received_qty = 0
			for item in mr.items:
				if item.item_code == self.production_item and item.ordered_qty!=item.qty and self.req_qty==item.qty:
					item.db_set("ordered_qty", self.req_qty)
				mr_per_ordered += item.ordered_qty
				mr_req_qty += item.qty 
				mr_received_qty += item.received_qty
			percentage_ordered = (mr_per_ordered)*100/mr_req_qty
			percentage_received = (mr_received_qty)*100/mr_req_qty
			if percentage_ordered < 100:
				mr.db_set("status","Partially Ordered")
			elif percentage_ordered==100 and percentage_received < 100:
				mr.db_set("status","Ordered")
			else:
				mr.db_set("status","Manufactured")
			mr.db_set("per_ordered", percentage_ordered)
			mr.db_set("per_received", percentage_received)

		if self.material_request and self.status=="Cancelled":
			mr = frappe.get_doc("Material Request", self.material_request)
			mr_per_ordered = 0
			mr_req_qty = 0
			mr_received_qty = 0
			for item in mr.items:
				if item.item_code == self.production_item and item.ordered_qty==item.qty and self.req_qty==item.qty:
					item.db_set("ordered_qty", 0)
				mr_per_ordered += item.ordered_qty
				mr_req_qty += item.qty 
				mr_received_qty += item.received_qty
			percentage_ordered = (mr_per_ordered)*100/mr_req_qty
			percentage_received = (mr_received_qty)*100/mr_req_qty
			mr.db_set("per_ordered", percentage_ordered)
			mr.db_set("per_received", percentage_received)
			mr.db_set("pipes_work_order",None)
			for item in self.required_items:
				batch = frappe.get_doc("Batch",item.batch_no)
				batch.db_set("pipes_work_order",None)

	def check_warehouses(self):
		throw_error = 0
		if not self.s_warehouse:
			frappe.msgprint(_("Source Warehouse missing"))
			throw_error = 1
		if not self.wip_warehouse and self.skip_transfer == 0:
			frappe.msgprint(_("Work-in-Progress Warehouse missing"))
			throw_error = 1
		if not self.t_warehouse:
			frappe.msgprint(_("Target Warehouse missing"))
			throw_error = 1
		if not self.scrap_warehouse:
			frappe.msgprint(_("Scrap Warehouse missing"))
			throw_error = 1
		if not self.a_quality_pipe_warehouse:
			frappe.msgprint(_("A Quality Pipe Warehouse missing"))
			throw_error = 1
		if not self.b_quality_pipe_warehouse:
			frappe.msgprint(_("B Quality Pipe Warehouse missing"))
			throw_error = 1	
		if not self.required_items:
			frappe.msgprint(_("Required items missing"))
			throw_error = 1
		if throw_error == 1:
			frappe.throw(_("Please correct!"))

	def check_s_warehouse(self):
		throw_error = 0
		if self.required_items:
			i = 1
			for item in self.required_items:
				if (self.s_warehouse != item.batch_warehouse and item.batch_qty == 0):
					frappe.msgprint("No stock avaiable for batch at row({0})".format(i))
					throw_error = 1

				elif (self.s_warehouse != item.batch_warehouse):
					frappe.msgprint(_("Source Warehouse does not match with Batch Warehouse in required items at row({0})".format(i)))
					throw_error = 1
				i +=1
			if throw_error == 1:
				frappe.throw(_("Please correct!"))


	def check_mr_pwo(self):
		if self.material_request:
			mr = frappe.get_doc("Material Request", self.material_request)
			if mr.pipes_work_order == None:
				mr.db_set("pipes_work_order",self.name)
			elif mr.pipes_work_order != self.name:
				frappe.throw("Pipes work order# {0} is already made for Material Request# {1}".format(mr.pipes_work_order,mr.name))
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
def stop_unstop(pipes_work_order,status):
	set_pwo_status(pipes_work_order,status)	
		

@frappe.whitelist()
def start(pipes_work_order):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	if pwo.produced_qty == 0 and pwo.mtf_manufacturing == 0:
			status = "Started"
	pwo.db_set("status",status)
	pwo.db_set("actual_start_date", get_datetime())

@frappe.whitelist()
def material_transfer(pipes_work_order,batch_no,item_code,batch_qty,batch_warehouse,wip_warehouse,status):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	for item in pwo.required_items:
		if item.batch_no == batch_no:
			item.db_set("status","Transferred")
	mtf_manufacturing_tmp = 0
	for item in pwo.required_items:
		if item.status == "Transferred":
			mtf_manufacturing_tmp += item.batch_qty
	pwo.db_set("mtf_manufacturing", mtf_manufacturing_tmp)
	mt = frappe.new_doc("Stock Entry")
	mt.update({
		"stock_entry_type": "Material Transfer for Manufacture",
		"pipes_work_order": pipes_work_order,
		"from_warehouse": batch_warehouse,
		"to_warehouse": wip_warehouse,
		"pipes_work_order": pipes_work_order
	})
	mt.append("items",{
		"s_warehouse": batch_warehouse,
		"t_warehouse": wip_warehouse,
		"item_code": item_code,
		"qty": batch_qty,
		"batch_no": batch_no
	})
	mt.save()
	mt.submit()
	
	#Updating Projected Quantities
	strip_source	= get_bin(item_code,batch_warehouse)
	source_strip_reserved_qty_for_production = strip_source.reserved_qty_for_production - float(batch_qty)
	update_projected_qty(item_code,batch_warehouse,None,None,source_strip_reserved_qty_for_production)

	strip_wip		= get_bin(item_code,wip_warehouse)
	wip_strip_indented_qty = strip_wip.indented_qty - float(batch_qty)
	update_projected_qty(item_code,wip_warehouse,wip_strip_indented_qty,None,None)
	
	#Updating Status of PWO
	set_pwo_status(pipes_work_order,status)

@frappe.whitelist()
def material_manufacture(pipes_work_order,manufacture_qty,status):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	#weight of item to manufacture
	total_pipe_weight = round((float(manufacture_qty)*pwo.weight),2)
	
	#Creating new Stock Entry
	mf = frappe.new_doc("Stock Entry")
	mf.update({
		"stock_entry_type": "Manufacture",
		"pipes_work_order": pipes_work_order
	})

	#Looping through batches to check if batch qty is enough
	temp_total_pipe_weight = total_pipe_weight
	for item in pwo.required_items:
		if	round(temp_total_pipe_weight,2) != 0:	
			wip_strip_reserved_qty_for_production = 0
			#If qty to manufacture == total qty produced + qty to process
			if ((round(pwo.produced_qty,2)+round(float(manufacture_qty),2))== round(pwo.qty,2)):
				if item.batch_qty != item.consumed_qty and item.status == "Transferred":
					mf.append("items",{
						"s_warehouse": pwo.wip_warehouse,
						"item_code": item.item_code,
						"qty": item.batch_qty-item.consumed_qty,
						"batch_no": item.batch_no	
					})
					wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
					wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production - (item.batch_qty-item.consumed_qty)
					wip_strip_reserved_qty_for_production = round(wip_strip_reserved_qty_for_production,2)
					temp_val = (round((item.batch_qty - item.consumed_qty),2))
					item.db_set("consumed_qty",item.batch_qty)
					update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,wip_strip_reserved_qty_for_production)
			
			#If qty to process is less than batch_qty
			elif (round((item.batch_qty - item.consumed_qty),2))>(temp_total_pipe_weight) and item.status == "Transferred":
				mf.append("items",{
					"s_warehouse": pwo.wip_warehouse,
					"item_code": item.item_code,
					"qty": round(temp_total_pipe_weight,2),
					"batch_no": item.batch_no	
				})
				temp_batch_qty = round(item.consumed_qty,2) + round(temp_total_pipe_weight,2)
				wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
				wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production -round(temp_total_pipe_weight,2)
				wip_strip_reserved_qty_for_production = round(wip_strip_reserved_qty_for_production,2)
				temp_val = (round((item.batch_qty - item.consumed_qty),2))
				item.db_set("consumed_qty",temp_batch_qty)
				update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,wip_strip_reserved_qty_for_production)
				temp_total_pipe_weight = 0
			#If qty to process is greater than batch_qty
			elif round((item.batch_qty - item.consumed_qty),2)<temp_total_pipe_weight and item.status == "Transferred":
				mf.append("items",{
					"s_warehouse": pwo.wip_warehouse,
					"item_code": item.item_code,
					"qty": round((item.batch_qty - item.consumed_qty),2),
					"batch_no": item.batch_no	
				})
				temp_total_pipe_weight = temp_total_pipe_weight - (round((item.batch_qty - item.consumed_qty),2))
				wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
				wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production - (round((item.batch_qty - item.consumed_qty),2))
				wip_strip_reserved_qty_for_production = round(wip_strip_reserved_qty_for_production,2)
				temp_val = (round((item.batch_qty - item.consumed_qty),2))
				item.db_set("consumed_qty",item.batch_qty)
				update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,wip_strip_reserved_qty_for_production)
				
	mf.save()
	temp_manufacture_qty = float(manufacture_qty)
	temp_basic_rate = round(mf.total_outgoing_value/temp_manufacture_qty,2)
	mf.append("items",{
		"t_warehouse": pwo.t_warehouse,
		"item_code": pwo.production_item,
		"qty": round(float(manufacture_qty),2),
		"basic_rate": temp_basic_rate
	})
	mf.save()
	mf.submit()

	#Updating PWO produced qty
	total_producded_qty = pwo.produced_qty + round(float(manufacture_qty),2)
	pwo.db_set("produced_qty",total_producded_qty)

	#Updating Material Request
	mr_per_ordered = 0
	mr_req_qty = 0
	mr_received_qty = 0
	mr = frappe.get_doc("Material Request",pwo.material_request)
	for item in mr.items:
		if item.item_code == pwo.production_item and item.ordered_qty==item.qty and item.ordered_qty!=item.received_qty and pwo.req_qty==item.qty:
			new_received_qty = item.received_qty + round(float(manufacture_qty),2)
			item.db_set("received_qty",new_received_qty)
		mr_per_ordered += item.ordered_qty													
		mr_req_qty += item.qty 
		mr_received_qty += item.received_qty
		percentage_ordered = (mr_per_ordered)*100/mr_req_qty
		percentage_received = (mr_received_qty)*100/mr_req_qty
		mr.db_set("per_ordered", percentage_ordered)
		mr.db_set("per_received", percentage_received)	
	if percentage_ordered < 100:
		mr.db_set("status","Partially Ordered")
	elif percentage_ordered==100 and percentage_received < 100:
		mr.db_set("status","Ordered")
	else:
		mr.db_set("status","Manufactured")									
	pipe_bin = get_bin(pwo.production_item,pwo.t_warehouse)
	new_planned_qty = pipe_bin.planned_qty - round(float(manufacture_qty),2)				#calculating new planned qty
	update_projected_qty(pwo.production_item,pwo.t_warehouse,None,new_planned_qty,None)		#Updating Bin
	update_pipe_details(pipes_work_order)
	set_pwo_status(pipes_work_order,status)													#Updating Status of PWO

@frappe.whitelist()
def quality_inspection(pipes_work_order,pipe_a_qty,pipe_b_qty):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	pipe_a_qty_temp = round(float(pipe_a_qty),2)
	pwo.db_set("no_of_a_quality_pipes",pwo.no_of_a_quality_pipes + pipe_a_qty_temp)
	pipe_b_qty_temp = round(float(pipe_b_qty),2)
	pwo.db_set("no_of_b_quality_pipes",pwo.no_of_b_quality_pipes + pipe_b_qty_temp)
	
	#Creating new Stock Entry
	mt = frappe.new_doc("Stock Entry")
	mt.update({
		"stock_entry_type": "Material Transfer",
		"from_warehouse": pwo.t_warehouse,
		"pipes_work_order": pipes_work_order
	})

	# Inserting A quality items
	if pipe_a_qty_temp!= 0:
		mt.append("items",{
			"s_warehouse": pwo.t_warehouse,
			"t_warehouse": pwo.a_quality_pipe_warehouse,
			"item_code": pwo.production_item,
			"qty": pipe_a_qty_temp
		})

	# Inserting B quality items
	if pipe_b_qty_temp!= 0:
		mt.append("items",{
			"s_warehouse": pwo.t_warehouse,
			"t_warehouse": pwo.b_quality_pipe_warehouse,
			"item_code": pwo.production_item,
			"qty": pipe_b_qty_temp
		})

	mt.save()
	mt.submit()
	set_pwo_status(pipes_work_order,"Quality Inspection")

@frappe.whitelist()
def scrap_trasnfer(pipes_work_order,pipe_jala_bora,phakra_pipe,bari_end_cut):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	pipe_jala_bora_temp = round(float(pipe_jala_bora),2)
	phakra_pipe_temp = round(float(phakra_pipe),2)
	bari_end_cut_temp = round(float(bari_end_cut),2)
	total_weight = pipe_jala_bora_temp + phakra_pipe_temp + bari_end_cut_temp

	#Creating new stock entry
	mf = frappe.new_doc("Stock Entry")
	mf.update({
		"stock_entry_type": "Manufacture",
		"pipes_work_order": pipes_work_order
	})

	#Looping throw batches
	total_weight_tmp = total_weight
	total_remaining_qty_temp = 0
	for item in pwo.required_items:
		if item.status == "Transferred":	
			total_remaining_qty_temp += round((item.batch_qty - item.consumed_qty),2)
	for item in pwo.required_items:
		if total_weight_tmp != 0:
			
			#Consuming all batches
			if total_weight==total_remaining_qty_temp and item.status == "Transferred":
				mf.append("items",{
					"s_warehouse": pwo.wip_warehouse,
					"item_code": item.item_code,
					"qty": round((item.batch_qty-item.consumed_qty),2),
					"batch_no": item.batch_no	
				})
				total_weight_tmp = total_weight_tmp - (item.batch_qty-item.consumed_qty)
				total_weight_tmp = round(total_weight_tmp,2)
				wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
				new_wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production - round((item.batch_qty-item.consumed_qty),2)
				new_wip_strip_reserved_qty_for_production = round(new_wip_strip_reserved_qty_for_production,2)
				#frappe.msgprint("total scrap weight {0}".format(total_weight_tmp))
				temp_val = (round((item.batch_qty - item.consumed_qty),2))
				item.db_set("consumed_qty",item.batch_qty)
				update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,new_wip_strip_reserved_qty_for_production)

			#Scrap is less than remaining batch qty
			elif total_weight_tmp<round((item.batch_qty - item.consumed_qty),2) and item.status == "Transferred":
				mf.append("items",{
					"s_warehouse": pwo.wip_warehouse,
					"item_code": item.item_code,
					"qty": total_weight_tmp,
					"batch_no": item.batch_no	
				})
				temp_batch_qty = round(item.consumed_qty,2) + total_weight_tmp
				wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
				new_wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production - total_weight_tmp
				temp_val = (round((item.batch_qty - item.consumed_qty),2))
				item.db_set("consumed_qty",temp_batch_qty)
				update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,new_wip_strip_reserved_qty_for_production)
				total_weight_tmp = 0
			
			#Scrap is greater than remaining batch qty
			elif total_weight_tmp>round((item.batch_qty - item.consumed_qty),2) and item.status == "Transferred":
				mf.append("items",{
					"s_warehouse": pwo.wip_warehouse,
					"item_code": item.item_code,
					"qty": round((item.batch_qty - item.consumed_qty),2),
					"batch_no": item.batch_no	
				})
				total_weight_tmp = total_weight_tmp - round((item.batch_qty - item.consumed_qty),2)
				wip_strip = get_bin(item.item_code,pwo.wip_warehouse)
				new_wip_strip_reserved_qty_for_production = wip_strip.reserved_qty_for_production - (round((item.batch_qty - item.consumed_qty),2))
				#frappe.msgprint("total scrap weight {0}".format(total_weight_tmp))
				temp_val = (round((item.batch_qty - item.consumed_qty),2))
				item.db_set("consumed_qty",item.batch_qty)
				update_projected_qty(item.item_code,pwo.wip_warehouse,None,None,new_wip_strip_reserved_qty_for_production)

	mf.save()
	temp_basic_rate = round(mf.total_outgoing_value/total_weight,2)
	
	if pipe_jala_bora_temp!=0:
		mf.append("items",{
			"t_warehouse": pwo.scrap_warehouse,
			"item_code": "Pipe Jala Bora",
			"qty": pipe_jala_bora_temp,
			"basic_rate": temp_basic_rate
		})
		pipe_jala_bora_temp += pwo.pipe_jala_bora
		pwo.db_set("pipe_jala_bora",pipe_jala_bora_temp)
	if phakra_pipe_temp!=0:
		mf.append("items",{
			"t_warehouse": pwo.scrap_warehouse,
			"item_code": "Phakra Pipe",
			"qty": phakra_pipe_temp,
			"basic_rate": temp_basic_rate
		})
		phakra_pipe_temp += pwo.phakra_pipe
		pwo.db_set("phakra_pipe",phakra_pipe_temp)

	if bari_end_cut_temp!=0:
		mf.append("items",{
			"t_warehouse": pwo.scrap_warehouse,
			"item_code": "Bari End Cut",
			"qty": bari_end_cut_temp,
			"basic_rate": temp_basic_rate
		})
		bari_end_cut_temp += pwo.bari_end_cut
		pwo.db_set("bari_end_cut",bari_end_cut_temp)
	mf.save()
	mf.submit()	

	set_pwo_status(pipes_work_order,"Quality Inspection")

def set_pwo_status(pipes_work_order,status):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	if status == "Stopped":
		pwo.db_set("status",status)
		return "stopped"	
	else:
		produced_qty_weight = round(pwo.produced_qty*pwo.weight,2)
		passed_qty_weight = round(pwo.weight*(pwo.no_of_a_quality_pipes+pwo.no_of_b_quality_pipes),2)
		total_scrap_weight = round(pwo.pipe_jala_bora+pwo.phakra_pipe+pwo.bari_end_cut,2)
		total_weight_produced = produced_qty_weight + total_scrap_weight
		total_weight_produced = round(total_weight_produced,1)
		total_weight_processed = passed_qty_weight+total_scrap_weight
		total_weight_processed = round(total_weight_processed,1)
		#if status == 'Resumed':
		if pwo.produced_qty == 0 and pwo.mtf_manufacturing == 0:
			status = "Started"
		elif pwo.mtf_manufacturing >0 and pwo.mtf_manufacturing!=pwo.total_required_material:
			status = "Material Partially Transfered"
		elif pwo.mtf_manufacturing == pwo.total_required_material and pwo.total_required_material!=total_weight_produced:
			status = "In Process"
		elif pwo.total_required_material!=total_weight_processed :
			status = "Quality Inspection"
		elif pwo.total_required_material==total_weight_processed :
			status = "Completed"
			pwo.db_set("actual_end_date",get_datetime())
			pipe_bin = get_bin(pwo.produciton_item,pwo.t_warehouse)
			new_pipe_planned_qty = round(pipe_bin.planned_qty) - (round(pwo.qty,2)- round(pwo.produced_qty))
			new_pipe_planned_qty = round(new_pipe_planned_qty,2)
			update_projected_qty(pwo.production_item,pwo.t_warehouse,None,new_pipe_planned_qty,None)
		pwo.db_set("status",status)
		pwo.reload()
		return "resumed"

def init_bin(item,warehouse):
	pwo_bin = get_bin(item,warehouse)
	if pwo_bin.reserved_qty == None:
		pwo_bin.db_set("reserved_qty",0)
	if pwo_bin.actual_qty == None:
		pwo_bin.db_set("actual_qty",0)
	if pwo_bin.ordered_qty == None:
		pwo_bin.db_set("ordered_qty",0)
	if pwo_bin.indented_qty == None:
		pwo_bin.db_set("indented_qty",0)	
	if pwo_bin.planned_qty == None:
		pwo_bin.db_set("planned_qty",0)
	if pwo_bin.projected_qty == None:
		pwo_bin.db_set("projected_qty",0)
	if pwo_bin.reserved_qty_for_production == None:
		pwo_bin.db_set("reserved_qty_for_production",0)
	if pwo_bin.reserved_qty_for_sub_contract == None:
		pwo_bin.db_set("reserved_qty_for_sub_contract",0)
	if pwo_bin.valuation_rate == None:
		pwo_bin.db_set("valuation_rate",0)
	if pwo_bin.stock_value == None:
		pwo_bin.db_set("stock_value",0)

def update_projected_qty(item,warehouse,indented_qty,planned_qty,reserved_qty_for_production):
	pwo_bin = get_bin(item,warehouse)
	# Dealing with None variables
	if indented_qty == None:
		indented_qty = round(pwo_bin.indented_qty,2)
	else:
		pwo_bin.db_set("indented_qty",round(indented_qty,2))
	if planned_qty == None:
		planned_qty = round(pwo_bin.planned_qty,2)
	else:
		pwo_bin.db_set("planned_qty",round(planned_qty,2))
	if reserved_qty_for_production == None:
		reserved_qty_for_production = round(pwo_bin.reserved_qty_for_production,2)
	else:
		pwo_bin.db_set("reserved_qty_for_production",round(reserved_qty_for_production,2))

	new_projected_qty = pwo_bin.actual_qty+				\
						pwo_bin.ordered_qty+			\
						indented_qty+					\
						planned_qty-					\
						pwo_bin.reserved_qty-			\
						reserved_qty_for_production
	pwo_bin.db_set("projected_qty",new_projected_qty)

def update_pipe_details(pipes_work_order):
	pwo = frappe.get_doc("Pipes Work Order",pipes_work_order)
	
	new_total_weight = pwo.produced_qty*pwo.weight
	pwo.db_set("total_weight",new_total_weight)

	new_total_length = pwo.produced_qty*pwo.length
	pwo.db_set("total_length",new_total_length)