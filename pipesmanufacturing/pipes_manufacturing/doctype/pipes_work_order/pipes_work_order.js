// Copyright (c) 2019, Havenir and contributors
// For license information, please see license.txt

// Function to at variables in string
function parse(str) {
    var args = [].slice.call(arguments, 1),
        i = 0;

    return str.replace(/%s/g, () => args[i++]);
}

frappe.ui.form.on('Pipes Work Order', {

	setup: function(frm){
		// setting query for items to be visible in list
		frm.set_query('production_item',function(doc){
			return {
				filters: {
					'item_code': ['like','%Pipe-MS%']
				}
			}
		});
		frm.set_query('scrap_item',function(doc){
			return {
				filters: {
					'item_group': ['like','%Scrap%']
				}
			}
		});
		// setting query for items to be visible in CHILD DOC list
		/*
		frm.fields_dict.required_items.grid.get_field('batch_no').get_query = function(){
			return {
				filters: {
					'name': ['like', '%STRIP-MS%']
				}
			}
		}*/
	},

	onload: function(frm) {
		if (!frm.doc.status)
			frm.doc.status = 'Draft';
		cur_frm.refresh_field('status');	
	},

	on_submit: function(frm){
		frm.doc.status = 'Not Started';
		cur_frm.refresh_field('status');
	},

	refresh: function(frm,cdt,cdn) {
		if (frm.doc.docstatus===0 && cur_frm.doc.production_item){
			var item_code = frappe.model.get_doc(cdt, cdn);
			if(item_code.production_item.includes("Pipe-MS",0)){
				var pipe_thickness = undefined;
				var pipe_width = undefined;
				frm.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
					args: {
						item_code: item_code.production_item,
						variant: 'Pipe'
					},
					callback: function(r){
						pipe_thickness = r.message.thickness;
						pipe_width = r.message.width;
						// making new strip name to pass as query
						var strip_name = parse('%STRIP-MS-%s',pipe_width);
						strip_name += parse(' MM-%s',pipe_thickness);
						strip_name += '.00 MM%'
						// setting query for items to be visible in CHILD DOC list
						frm.fields_dict.required_items.grid.get_field('batch_no').get_query = function(){
							return {
								filters: {
									'item': ['like', strip_name],
									'batch_stock_status' : ['like', 'Available']
								}
							}
						}
					}
				})
				//calculating weight
                frm.call({
                    method: "steelpipes.sp_delivery_note.sp_delivery_note_item.calculate_pipe_weight_um",
                    args: {itemcode: item_code.production_item, um: 'Kg'},
                    callback:function(r){
                        var weight_um_temp         = r.message.item_weight_um;
                        var length_um_temp         = r.message.item_length_um;
             
                        if (item_code.qty == undefined || item_code.qty == 0 ){
                            var total_weight_um_temp   = weight_um_temp * 1;
                            var total_length_um_temp   = length_um_temp * 1;
                        }
                        else{
                            var total_weight_um_temp   = weight_um_temp * item_code.produced_qty;
                            var total_length_um_temp   = length_um_temp * item_code.produced_qty;
                        }

                        frappe.model.set_value(cdt, cdn, "weight", weight_um_temp);
                        frappe.model.set_value(cdt, cdn, "total_weight", total_weight_um_temp);
                        frappe.model.set_value(cdt, cdn, "length", length_um_temp);
						frappe.model.set_value(cdt, cdn, "total_length", total_length_um_temp);
                    }
				})
			}
		}
		erpnext.pipes_work_order.set_custom_buttons(frm,cdt,cdn);
		if (frm.doc.docstatus===1) {
			frm.trigger('show_progress');
		}
	},

	show_progress: function(frm) {
		// pipes progess bar
		var pipes_bar = [];
		var pipes_message = "";
		var pipes_added_min = false;
		var pipes_inspected = cur_frm.doc.no_of_a_quality_pipes + cur_frm.doc.no_of_b_quality_pipes;
		// produced_qty
		var pipes_title = __("{0} items produced in which {1} have been inspected", [frm.doc.produced_qty, pipes_inspected]);
		pipes_bar.push({
			"title": pipes_title,
			"width": ((frm.doc.no_of_a_quality_pipes + frm.doc.no_of_b_quality_pipes)/frm.doc.produced_qty * 100) + "%",
			"progress_class": "progress-bar-success"
		});
		if (pipes_bar[0].width == "0%"){
			pipes_bar[0].width = "0.5%";
			pipes_added_min = 0.5;
		}

		pipes_message = pipes_title;
		if (frm.doc.produced_qty>0){
			frm.dashboard.add_progress(__('Status'), pipes_bar, pipes_message);
		}

		var strip_bar = [];
		var strip_message = "";
		var strip_added_min = "";

		// transferred qty
		var strip_title = __("{0} kg raw material transferred", [frm.doc.mtf_manufacturing]);
		strip_bar.push({
			"title": strip_title,
			"width": ((frm.doc.mtf_manufacturing/frm.doc.total_required_material)*100 + "%"),
			"progress_class": "progress-bar-striped"
		});
		if (strip_bar[0].width == "0%"){
			strip_bar[0].width == "0.5%";
			pipes_added_min = 0.5;
		}

		strip_message = strip_title;
		if (frm.doc.mtf_manufacturing>0){
			frm.dashboard.add_progress(__("Status"), strip_bar, strip_message);
		}
	},

	production_item: function(frm,cdt,cdn){
		var item_code = frappe.model.get_doc(cdt, cdn);
        if (item_code.production_item){
            if(item_code.production_item.includes("Pipe-MS",0)){
				var pipe_thickness = undefined;
				var pipe_width = undefined;
				frm.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
					args: {
						item_code: item_code.production_item,
						variant: 'Pipe'
					},
					callback: function(r){
						pipe_thickness = r.message.thickness;
						pipe_width = r.message.width;
						// making new strip name to pass as query
						var strip_name = parse('%STRIP-MS-%s',pipe_width);
						strip_name += parse(' MM-%s',pipe_thickness);
						strip_name += '.00 MM%'
						// setting query for items to be visible in CHILD DOC list
						frm.fields_dict.required_items.grid.get_field('batch_no').get_query = function(){
							return {
								filters: {
									'item': ['like', strip_name],
									'batch_stock_status' : ['like', 'Available']
								}
							}
						}

					}
				})
				//calculating weight
                frm.call({
                    method: "steelpipes.sp_delivery_note.sp_delivery_note_item.calculate_pipe_weight_um",
                    args: {itemcode: item_code.production_item, um: 'Kg'},
                    callback:function(r){
                        var weight_um_temp         = r.message.item_weight_um;
                        var length_um_temp         = r.message.item_length_um;
             
                        if (item_code.qty == undefined || item_code.qty == 0 ){
                            var total_weight_um_temp   = weight_um_temp * 1;
                            var total_length_um_temp   = length_um_temp * 1;
                        }
                        else{
                            var total_weight_um_temp   = weight_um_temp * item_code.produced_qty;
                            var total_length_um_temp   = length_um_temp * item_code.produced_qty;
                        }

                        frappe.model.set_value(cdt, cdn, "weight", weight_um_temp);
                        frappe.model.set_value(cdt, cdn, "total_weight", total_weight_um_temp);
                        frappe.model.set_value(cdt, cdn, "length", length_um_temp);
						frappe.model.set_value(cdt, cdn, "total_length", total_length_um_temp);
                    }
				})
            }
        }
        else{
            frappe.model.set_value(cdt,cdn, "item_name", null);
		}
	}
});

frappe.ui.form.on('Pipes Work Order Item', {

	batch_no: function(frm,cdt,cdn){
		if(cur_frm.doc.production_item == undefined){
			frappe.throw('Please first set Pipe to Manufacture');
		}
		var childdoc = frappe.model.get_doc(cdt,cdn);
		if(childdoc.batch_no){
			frm.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Batch',
					name: childdoc.batch_no 
				},
				callback(r){
					if(r.message){
						var batch_doc = r.message;
						var pipe_thickness = undefined;
						var pipe_width = undefined;
						var strip_thickness = undefined;
						var strip_width = undefined;
						frm.call({
							method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
							args: {
								item_code: batch_doc.item,
								variant: 'Strip-MS'
							},
							callback: function(r){
								strip_thickness = r.message.thickness;
								strip_width = r.message.width;
							}
						})

						frm.call({
							method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
							args: {
								item_code: cur_frm.doc.production_item,
								variant: 'Pipe'
							},
							callback: function(r){
								pipe_thickness = r.message.thickness;
								pipe_width = r.message.width;
							}
						})
						if (pipe_width==strip_width && pipe_thickness==strip_thickness){
							frappe.model.set_value(cdt,cdn,'item_code',batch_doc.item);
							frm.call({
								method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
								args: {batch_no: batch_doc.name},
								callback: function(r){
									r.message.sort(function(a, b) { a.qty > b.qty ? 1 : -1 });
									var batch_msg = r.message;
									var total_batch_qty = 0;
									var batch_warehouse_temp = undefined;
									(r.message || []).forEach(function(d) {
										if(d.qty>0){
											if(cur_frm.doc.s_warehouse == d.warehouse){
												total_batch_qty +=d.qty;
												batch_warehouse_temp = d.warehouse;
											}
										}
									});
									frappe.model.set_value(cdt,cdn,'batch_qty', total_batch_qty);
									frappe.model.set_value(cdt,cdn,'batch_warehouse', batch_warehouse_temp);
									var sum_of_batch_weight = 0;
									for (var i in cur_frm.doc.required_items){
										sum_of_batch_weight += cur_frm.doc.required_items[i].batch_qty;
									}
									cur_frm.doc.total_required_material = sum_of_batch_weight;
									cur_frm.doc.qty = sum_of_batch_weight/cur_frm.doc.weight;
									cur_frm.refresh_field('qty');
									cur_frm.refresh_field('total_required_material');

								}
							})
						}
						else{
							if(strip_thickness!=pipe_thickness){
								frappe.msgprint('Thickness does not match');
							}
							else if (strip_width!=pipe_width){
								frappe.msgprint('Width does not match');
							}
							else{
								frappe.msgprint('Thickness and width does not match');
							}
							frappe.throw('Please enter correct required item!');
						}
					}
				}
			});
		}	
	},

	required_items_remove: function(frm, cdt, cdn){
		var sum_of_batch_weight = 0;
		for (var i in cur_frm.doc.required_items){
			sum_of_batch_weight += cur_frm.doc.required_items[i].batch_qty;
		}
		cur_frm.doc.total_required_material = sum_of_batch_weight;
		cur_frm.doc.qty = sum_of_batch_weight/cur_frm.doc.weight;
		cur_frm.refresh_field('qty');
		cur_frm.refresh_field('total_required_material');
	},

	required_items_add: function(frm, cdt, cdn){
		if (cur_frm.doc.production_item.includes("Pipe-MS",0)){
			var production_item_temp = cur_frm.doc.production_item;
			var pipe_thickness = undefined;
			var pipe_width = undefined;
			frm.call({
				method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
				args: {
					item_code: production_item_temp,
					variant: 'Pipe'
				},
				callback: function(r){
					pipe_thickness = r.message.thickness;
					pipe_width = r.message.width;
					// making new strip name to pass as query
					var strip_name = parse('%Strip-MS-%s',pipe_width);
					strip_name += parse(' MM-%s',pipe_thickness);
					strip_name += '.00 MM%'
					var batch_no_already_added = [];
					for (var i in cur_frm.doc.required_items){
						if (cur_frm.doc.required_items[i].item_code){
							if (strip_name.includes(cur_frm.doc.required_items[i].item_code,0)){
								if(cur_frm.doc.required_items[i].item_code){
									batch_no_already_added.push(cur_frm.doc.required_items[i].batch_no);
								}
							}
						}
					}
					// setting query for items to be visible in CHILD DOC list
					frm.fields_dict.required_items.grid.get_field('batch_no').get_query = function(){
						return {
							filters: {
								'name': ['not in', batch_no_already_added],
								'item': ['like', strip_name],
								'batch_stock_status' : ['like', 'Available'],
								'pipes_work_order' : ['like','']
							}
						}
					}
				}
			})
		}
	}
});

erpnext.pipes_work_order = {
	set_custom_buttons: function(frm,cdt,cdn) {
		var doc = frm.doc;
		var total_produced_pipe_weight = parseFloat((doc.produced_qty*doc.weight).toFixed(2));
		total_produced_pipe_weight = parseFloat(total_produced_pipe_weight.toFixed(2))
		//console.log("Total pipe produced: " + total_produced_pipe_weight)
		var passed_qty_weight = parseFloat((doc.weight*(doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes)).toFixed(2));
		passed_qty_weight = parseFloat(passed_qty_weight.toFixed(2))
		//console.log("Total QC weight: " + passed_qty_weight)
		var total_scrap_weight = parseFloat(doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut);
		total_scrap_weight = parseFloat(total_scrap_weight.toFixed(2))
		//console.log("Total scrap: " + total_scrap_weight)
		var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
		total_weight_produced = parseFloat(total_weight_produced.toFixed(1)	)
		//console.log("Total weight produced: " + total_weight_produced)
		var total_weight_processed = passed_qty_weight + total_scrap_weight;
		total_weight_processed = parseFloat(total_weight_processed.toFixed(1))
		//console.log("Total weight processed: " + total_weight_processed)
		//console.log("")
		if (doc.docstatus===1) {
			//frm.page.add_menu_item(__("Send SMS"), function() {
			//	var sms_man = new SMSManager(doc);
			//})

			// adding buttons to stop and reopen a Pipe work order
			if (doc.status != 'Not Started' && doc.status != 'Completed' && doc.status != "Stopped") {
				var btn1 = frm.add_custom_button(__('Stop'), function() {
					erpnext.pipes_work_order.stop_pipes_work_order(frm, "Stopped");
				}, __("Status"));
				//btn1.addClass("btn-danger");
			} else if (doc.status == 'Stopped') {
				var btn1 = frm.add_custom_button(__('Re-open'), function() {
					erpnext.pipes_work_order.stop_pipes_work_order(frm, "Resumed");
				}, __("Status"));
				//btn1.addClass("btn.danger");
			}
			if (doc.status == "Not Started"){
				var btn1 = frm.add_custom_button(__('Start'), function(){
					erpnext.pipes_work_order.start_pipes_work_order(frm);
				});
				btn1.addClass('btn-primary');
			}
			else if (doc.status == "Started" && (doc.mtf_manufacturing != doc.total_required_material)){
				var btn1 = frm.add_custom_button(__('Material Transfer'), function(){
					erpnext.pipes_work_order.material_transfer(frm,cdt,cdn, "Started");
				}, __("Create"));
			}
			if (doc.status == "Material Partially Transfered" && (doc.mtf_manufacturing != doc.total_required_material)){
				var btn1 = frm.add_custom_button(__('Material Transfer'), function(){
					erpnext.pipes_work_order.material_transfer(frm,cdt,cdn,"Material Partially Transfered");
				}, __("Create"));
				if (doc.mtf_manufacturing!=total_weight_produced){
					var btn2 = frm.add_custom_button(__('Manufacture'), function(){
						erpnext.pipes_work_order.material_manufacture(frm,cdt,cdn, "Material Partially Transfered");
					}, __("Create"));
				}
				if (doc.produced_qty>0){
					var produced_weight = doc.produced_qty*doc.weight;
					produced_weight = produced_weight.toFixed(2);
					var processed_weight = 
							doc.no_of_a_quality_pipes*doc.weight +
							doc.no_of_b_quality_pipes*doc.weight +
							doc.pipe_jala_bora +
							doc.phakra_pipe +
							doc.bari_end_cut;
							
					processed_weight = processed_weight.toFixed(2);
					if (produced_weight-processed_weight>0){
						var btn3 = frm.add_custom_button(__('Quality Inspection'), function(){
						erpnext.pipes_work_order.quality_inspection(frm,cdt,cdn);
						}, __("Create"));
					}

					var temp_val = parseFloat((doc.produced_qty*doc.weight).toFixed(2)) + parseFloat(doc.pipe_jala_bora) + parseFloat(doc.phakra_pipe) + parseFloat(doc.bari_end_cut) 
					if (temp_val!=doc.mtf_manufacturing){
						var btn4 = frm.add_custom_button(__('Scrap'), function(){
							erpnext.pipes_work_order.scrap_transfer(frm,cdt,cdn);
						}, __("Create"));
					}
					
				}
			}
			else if (doc.status == "In Process" && (doc.mtf_manufacturing!=total_weight_produced)){
				var btn1 = frm.add_custom_button(__('Manufacture'), function(){
					erpnext.pipes_work_order.material_manufacture(frm,cdt,cdn, "In Process");
				},__("Create"));
				if (doc.produced_qty>0){
					var produced_weight = doc.produced_qty*doc.weight;
					produced_weight = produced_weight.toFixed(2);
					var processed_weight = 
							doc.no_of_a_quality_pipes*doc.weight +
							doc.no_of_b_quality_pipes*doc.weight +
							doc.pipe_jala_bora +
							doc.phakra_pipe +
							doc.bari_end_cut;
							
					processed_weight = processed_weight.toFixed(2);
					if (produced_weight-processed_weight>0){
						var btn2 = frm.add_custom_button(__('Quality Inspection'), function(){
							erpnext.pipes_work_order.quality_inspection(frm,cdt,cdn);
						}, __("Create"));
					}
					var temp_val = parseFloat((doc.produced_qty*doc.weight).toFixed(2)) + parseFloat(doc.pipe_jala_bora) + parseFloat(doc.phakra_pipe) + parseFloat(doc.bari_end_cut) 
					if (temp_val!=doc.mtf_manufacturing){
						var btn3 = frm.add_custom_button(__('Scrap'), function(){
							erpnext.pipes_work_order.scrap_transfer(frm,cdt,cdn);
						}, __("Create"));
					}
				}
			}
			else if (doc.status == "Quality Inspection" && doc.total_required_material!=total_weight_processed){
				if (doc.produced_qty>0){
					var produced_weight = doc.produced_qty*doc.weight;
					produced_weight = produced_weight.toFixed(2);
					var processed_weight = 
							doc.no_of_a_quality_pipes*doc.weight +
							doc.no_of_b_quality_pipes*doc.weight +
							doc.pipe_jala_bora +
							doc.phakra_pipe +
							doc.bari_end_cut;
							
					processed_weight = processed_weight.toFixed(2);
					if (produced_weight-processed_weight>0){
						var btn2 = frm.add_custom_button(__('Quality Inspection'), function(){
							erpnext.pipes_work_order.quality_inspection(frm,cdt,cdn);
						}, __("Create"));
					}
					var temp_val = parseFloat((doc.produced_qty*doc.weight).toFixed(2)) + parseFloat(doc.pipe_jala_bora) + parseFloat(doc.phakra_pipe) + parseFloat(doc.bari_end_cut) 
					if (temp_val!=doc.mtf_manufacturing){
						var btn3 = frm.add_custom_button(__('Scrap'), function(){
							erpnext.pipes_work_order.scrap_transfer(frm,cdt,cdn);
						}, __("Create"));
					}
				}
			}
		}
	},
	stop_pipes_work_order: function(frm, status) {
		if (status == "Stopped"){
			frappe.confirm(
				"Are you sure you want to stop this order?",
				//function on yes
				function(){
					if (status == "Stopped"){
						frappe.call({
							method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.stop_unstop",
							args: {
								pipes_work_order: frm.doc.name,
								status: status
							},
							callback: function(r) {
								frm.reload_doc();
								var alertmsg = "Pipe production order " + frm.doc.name + " stopped";
								frappe.show_alert(alertmsg,3)
							}
						})
					}
				},
				function(){
					frappe.show_alert("Lets keep going :)")
				}
			)
		}
		else{
			frappe.call({
				method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.stop_unstop",
				args: {
					pipes_work_order: frm.doc.name,
					status: status
				},
				callback: function(r) {
					frm.reload_doc();
					var alertmsg = "Pipe production order " + frm.doc.name + " resumed";
					frappe.show_alert(alertmsg,3)
				}
			})
		}

	},

	start_pipes_work_order: function(frm) {
		frappe.call({
			method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.start",
			args: {
				pipes_work_order: frm.doc.name
			},
			callback: function(r) {
				frm.reload_doc();
			}
		})
	},

	material_transfer: function(frm,cdt,cdn, status) {
		let batch_list_items = [];
		var j = 0;
		for (var i in cur_frm.doc.required_items){
			if (cur_frm.doc.required_items[i].status == "Not Transferred"){0
				batch_list_items[j] = cur_frm.doc.required_items[i];
				j ++;
			}
		}
		let d = new frappe.ui.Dialog({
			title: __("Select Batch for Transfer"),
			fields: [
				{
					label: "Select Batch",
					fieldname: "batch_list",
					fieldtype: "Table",
					fields: [
						{
							fieldtype:'Data',
							fieldname:'batch_no',
							label: __('Batch No'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Data',
							fieldname:'item_code',
							label: __('Item code'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'float',
							fieldname:'batch_qty',
							label: __('Quantity'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Data',
							fieldname:'batch_warehouse',
							label: __('Warehouse'),
							read_only:1,
							in_list_view:1
						}
					],
					data: batch_list_items,
					get_data: function() {
						return batch_list_items
					}
				},
			],
			primary_action_label: 'Trasnfer',
			primary_action(values) {
				var args = d.get_values();
				let selected_items = d.fields_dict.batch_list.grid.get_selected_children()
				if(selected_items.length == 0) {
					frappe.throw({message: 'Please select Item form Table', title: __('Message'), indicator:'blue'})
				}
				let selected_items_list = []
				for(let i in selected_items){
					selected_items_list.push(selected_items[i])
				}

				for (let i in selected_items_list){
					frappe.call({
						method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.material_transfer",
						args: {
							pipes_work_order: frm.doc.name,
							batch_no: selected_items_list[i].batch_no,
							item_code: selected_items_list[i].item_code,
							batch_qty: selected_items_list[i].batch_qty,
							batch_warehouse: selected_items_list[i].batch_warehouse,
							wip_warehouse: cur_frm.doc.wip_warehouse,
							status: status
						},
						callback: function(r) {
							frm.reload_doc();
						}
					})
				}
				d.hide();
				frm.reload_doc();
				frappe.show_alert("Material Transferred",3)
			}
		});
		d.show();	
	},

	material_manufacture: function(frm,cdt,cdn,status) {
		var doc = frm.doc;
		var total_produced_pipe_weight = parseFloat((doc.produced_qty*doc.weight).toFixed(2));
		var passed_qty_weight = parseFloat((doc.weight*(doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes)).toFixed(2));
		var total_scrap_weight = parseFloat(doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut);
		var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
		var total_weight_processed = passed_qty_weight + total_scrap_weight;
		var maf_manufacturing = doc.mtf_manufacturing - total_weight_produced;
		var paf_manufacturing = (maf_manufacturing/doc.weight).toFixed(2);
		let d = new frappe.ui.Dialog({
			title: 'Enter details',
			fields: [
				{
					label: 'Pipe To Manufacture',
					fieldname: 'production_item',
					fieldtype: 'Link',
					read_only: 1,
					default: doc.production_item,
				},
				{
					fieldtype: "Column Break"
				},
				{
					label: 'Pipe Quanity',
					fieldname: 'pipe_qty',
					fieldtype: 'Float',
					default: undefined,
					precision: 2
				},
				{
					label: 'Pipes that can be manufactures',
					fieldname: 'pipes_tcbm',
					fieldtype: 'Float',
					default: paf_manufacturing,
					precision: 2,
					read_only: 1
				}
			],
			primary_action_label: 'Manufacture',
			primary_action(values) {
				if (values.pipe_qty == undefined){
					frappe.throw("Please Enter a value")
				}
				if ((values.pipe_qty-paf_manufacturing)>0){
					frappe.throw("Not enough raw material in Work In Progress Warehouse");
				}
				d.hide();
				frappe.call({
					method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.material_manufacture",
					args: {
						pipes_work_order: frm.doc.name,
						manufacture_qty: values.pipe_qty,
						status: status
					},
					callback: function(r) {
						frm.reload_doc();
						var alertmsg = values.pipe_qty + " Pipes manufactured";
						frappe.show_alert(alertmsg ,3);
					}
				})
			}
		});
		d.show();
	},
	scrap_transfer: function(frm,cdt,cdn){
		var doc = frm.doc;
		var total_produced_pipe_weight = doc.produced_qty*doc.weight;
		var passed_qty_weight = (doc.weight*(doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes)).toFixed(2);
		var total_scrap_weight = (doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut);
		var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
		var total_weight_processed = passed_qty_weight + total_scrap_weight;
		var raw_material_remaining = 0;
		for (var i in doc.required_items){
			if (doc.required_items[i].status == "Transferred")
				raw_material_remaining += doc.required_items[i].batch_qty - doc.required_items[i].consumed_qty;
		}
		raw_material_remaining = parseFloat(raw_material_remaining.toFixed(2))

		let d = new frappe.ui.Dialog({
			title: "Enter details in (Kg)",
			fields:[
				{
					label: 'Pipe Jala Bora',
					fieldname: 'pipe_jala_bora',
					fieldtype: 'Float',
					default: 0,
					precision: 2
				},
				{
					label: 'Pipe Phakra',
					fieldname: 'phakra_pipe',
					fieldtype: 'Float',
					default: 0,
					precision: 2
				},
				{
					label: 'Bari End Cut',
					fieldname: 'bari_end_cut',
					fieldtype: 'Float',
					default: 0,
					precision: 2
				},
				{
					label: 'Remaining Raw Material',
					fieldname: 'raw_material',
					fieldtype: 'Float',
					precision: 2,
					read_only: 1,
					default: raw_material_remaining
				}
			],
			primary_action_label: "Process",
			primary_action(values){
				if (values.pipe_jala_bora== undefined){
					values.pipe_jala_bora = 0;
				}
				if (values.phakra_pipe == undefined){
					values.phakra_pipe = 0;
				}
				if (values.bari_end_cut == undefined){
					values.bari_end_cut = 0;
				}
				var total_scrap_tmp = values.pipe_jala_bora+values.phakra_pipe+values.bari_end_cut;
				if (total_scrap_tmp == 0){
					frappe.throw("Please enter values")
				}
				if (total_scrap_tmp>raw_material_remaining.toFixed(2)){
					frappe.throw("Cannot Process Scrap Quanity greater than Remaining Raw Material");
				}
				d.hide();
				frappe.call({
					method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.scrap_trasnfer",
					args: {
						pipes_work_order: frm.doc.name,
						pipe_jala_bora: values.pipe_jala_bora,
						phakra_pipe: values.phakra_pipe,
						bari_end_cut: values.bari_end_cut,
						status: "Quality Inspection"
					},
					callback: function(r) {
						frm.reload_doc();
						var alertmsg = "Scrap Processed";
						frappe.show_alert(alertmsg ,3);
					}
				})
			}
		});
		d.show();
	},
	quality_inspection: function(frm,cdt,cdn){
		var doc = frm.doc;
		var total_produced_pipe_weight = doc.produced_qty*doc.weight;
		var passed_qty_weight = (doc.weight*(doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes)).toFixed(2);
		var total_scrap_weight = (doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut);
		var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
		var total_weight_processed = passed_qty_weight + total_scrap_weight;
		var raw_material_remaining = doc.total_required_material-total_weight_produced;
		var qty_remaining_for_qi = doc.produced_qty-doc.no_of_a_quality_pipes-doc.no_of_b_quality_pipes
		let d = new frappe.ui.Dialog({
			title: "Quality Inspection",
			fields:[
				{
					label: 'Item',
					fieldname: 'item_code',
					fieldtype: 'Data',
					default: cur_frm.doc.production_item,
					read_only: 1
				},
				{
					fieldtype: 'Column Break',
				},
				{
					label: 'Remaing Pipes to be Inspected',
					fieldname: 'pipes_to_be_inspected',
					fieldtype: 'Float',
					precision: 2,
					default: qty_remaining_for_qi,
					read_only: 1
				},
				{
					fieldtype: 'Section Break',
				},
				{
					label: 'No of A Quality Pipes',
					fieldname: 'pipe_a_qty',
					fieldtype: 'Float',
					default: 0,
					precision: 2
				},
				{
					fieldtype: 'Column Break',
				},
				{
					label: 'No of B Quality Pipes',
					fieldname: 'pipe_b_qty',
					fieldtype: 'Float',
					default: 0,
					precision: 2
				},
			],
			primary_action_label: "Process",
			primary_action(values){
				if (values.pipe_a_qty == undefined){
					values.pipe_a_qty = 0;
				}
				if (values.pipe_b_qty == undefined){
					values.pipe_b_qty = 0;
				}
				var total_qty_tmp = values.pipe_a_qty+values.pipe_b_qty;
				if (total_qty_tmp==0){
					frappe.throw("Please enter values")
				}
				if (total_qty_tmp>values.pipes_to_be_inspected){
					frappe.throw("This many pipes not avaible for inspection");
				}
				d.hide();
				frappe.call({
					method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.quality_inspection",
					args: {
						pipes_work_order: frm.doc.name,
						pipe_a_qty: values.pipe_a_qty,
						pipe_b_qty: values.pipe_b_qty,
						status: "Quality Inspection"
					},
					callback: function(r) {
						frm.reload_doc();
						var alertmsg = "Pipes Processed";
						frappe.show_alert(alertmsg ,3);
					}
				})
			}
		});
		d.show();
	}
}