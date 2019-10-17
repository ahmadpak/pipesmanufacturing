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
    },

    refresh: function(frm,cdt,cdn){
        var doc = cur_frm.doc;
        if (doc.docstatus == 0 && doc.production_item){
            //calculating weight
            if (doc.weight == 0 || doc.weight == undefined){
                frm.call({
                    method: "steelpipes.sp_delivery_note.sp_delivery_note_item.calculate_pipe_weight_um",
                    args: {itemcode: doc.production_item, um: 'Kg'},
                    callback:function(r){
                        var weight_um_temp         = r.message.item_weight_um;
                        var length_um_temp         = r.message.item_length_um;

                        frappe.model.set_value(cdt, cdn, "weight", weight_um_temp);
                        frappe.model.set_value(cdt, cdn, "length", length_um_temp);
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
})

frappe.ui.form.on('Pipes Work Order Item', {
    batch_no: function(frm,cdt,cdn){
        var child_item = frappe.model.get_doc(cdt,cdn);
        if (child_item.batch_no){
            var doc = cur_frm.doc;
            frm.call({
                method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.batch_qty',
                args: {
                    batch_no: child_item.batch_no,
                    s_warehouse: doc.s_warehouse
                },
                callback: function(r){
                    frappe.model.set_value(cdt,cdn,'batch_qty',r.message.available_qty);
                    frappe.model.set_value(cdt,cdn,'item_code',r.message.required_item);
                    frappe.model.set_value(cdt,cdn,'batch_warehouse',doc.s_warehouse);
                    frappe.model.set_value(cdt,cdn, 'status','Not Transferred');
                    //Looping through required items to calculate values
                    var total_required_item_tmp = 0;
                    for (var i in doc.required_items){
                        total_required_item_tmp+=doc.required_items[i].batch_qty;
                    }
                    doc.total_required_material = total_required_item_tmp;
                    cur_frm.refresh_field('total_required_material');
                    doc.qty = Math.floor(total_required_item_tmp/doc.weight);
                    cur_frm.refresh_field('qty');
                }
            })
        }
    },
    required_items_remove: function(frm,cdt,cdn){
        var doc = cur_frm.doc;
        var total_required_item_tmp = 0;
        for (var i in doc.required_items){
            total_required_item_tmp+=doc.required_items[i].batch_qty;
        }
        doc.total_required_material = total_required_item_tmp;
        cur_frm.refresh_field('total_required_material');
        doc.qty = (total_required_item_tmp/doc.weight).toFixed(0);
        cur_frm.refresh_field('qty');
    },
    required_items_add: function(frm, cdt, cdn){
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
})

erpnext.pipes_work_order = {
	set_custom_buttons: function(frm,cdt,cdn) {
        var doc = cur_frm.doc;
        var total_produced_pipe_weight = parseFloat((doc.produced_qty*doc.weight).toFixed(2));
        var total_qc_pipes = parseInt(doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes);
        var total_scrap_weight = parseFloat(doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut);
		var total_weight_produced = parseFloat(total_produced_pipe_weight+total_scrap_weight);
		var maf_manufacturing = (doc.mtf_manufacturing - total_weight_produced).toFixed(2);
        var paf_manufacturing = Math.floor(maf_manufacturing/doc.weight);
        if (doc.docstatus===1) {
        // adding buttons to start, stop and reopen the Work Order
			if (doc.status != 'Not Started' && doc.status != 'Completed' && doc.status != "Stopped") {
				var btn1 = frm.add_custom_button(__('Stop'), function() {   //Button to stop Work Order
					erpnext.pipes_work_order.stop_unstop(frm, "stop");
                }, __("Status"));
                if (doc.status == "Started"){  
                    var btn1 = frm.add_custom_button(__('Material Transfer'), function() {  //Adding button to transfer raw material
                        erpnext.pipes_work_order.material_transfer(frm,cdt,cdn, 'Material Transfer');
                    }, __("Create"));
                }
            } 
            else if (doc.status == 'Stopped') { 
				var btn1 = frm.add_custom_button(__('Re-open'), function() {    //Button to resume Work Order
					erpnext.pipes_work_order.stop_unstop(frm, "resume");
				}, __("Status"));
            }
            else if (doc.status == 'Not Started'){
                var btn1 = frm.add_custom_button(__('Start'), function() {  //Button to start Work Order
					erpnext.pipes_work_order.stop_unstop(frm, 'start');
				});
				btn1.addClass("btn-primary");
            }
        // Adding buttons to transfer raw material, manufacture pipe, inspect pipe and update scrap produced 
            if (doc.status == 'Material Partially Transfered'){
                var btn1 = frm.add_custom_button(__('Material Transfer'), function() {  //Button to transfer raw material
					erpnext.pipes_work_order.material_transfer(frm,cdt,cdn, 'Material Transfer');
				}, __("Create"));
                if (paf_manufacturing!=0){
                    var btn2 = frm.add_custom_button(__('Pipe Manufacture'), function() {   //Button to manufacture pipe
                        erpnext.pipes_work_order.material_manufacture(frm, 'Material Manufacture');
					}, __("Create"));
				}
				if (total_weight_produced!=doc.mtf_manufacturing){
                    var btn3 = frm.add_custom_button(__('Scrap'), function() {  //Button to update scrap produced
                        erpnext.pipes_work_order.material_scrap(frm, 'Scrap');
                    }, __("Create"));
                }
                if (total_qc_pipes!=doc.produced_qty){
                    var btn4 = frm.add_custom_button(__('Quality Inspection'), function() { //Button to inspect pipe produced
                        erpnext.pipes_work_order.material_inspection(frm, 'Quality Inspection');
                    }, __("Create"));
                }
            }
        // Adding buttons to inspect pipe and update scrap produced
            else if (doc.status == 'In Process'){
                if (paf_manufacturing!=0){
                    var btn1 = frm.add_custom_button(__('Pipe Manufacture'), function() {   //Button to manufacture pipe
                        erpnext.pipes_work_order.material_manufacture(frm, 'Material Manufacture');
					}, __("Create"));
				}
				if (total_weight_produced!=doc.mtf_manufacturing){
                    var btn2 = frm.add_custom_button(__('Scrap'), function() {  //Button to update scrap produced
                        erpnext.pipes_work_order.material_scrap(frm, 'Scrap');
                    }, __("Create"));
                }
                if (total_qc_pipes!=doc.produced_qty){
                    var btn3 = frm.add_custom_button(__('Quality Inspection'), function() { //Button to inspect pipe produced
                        erpnext.pipes_work_order.material_inspection(frm, 'Quality Inspection');
                    }, __("Create"));
                }
			}
			else if (doc.status == 'Quality Inspection'){
				var btn1 = frm.add_custom_button(__('Quality Inspection'), function() { //Button to inspect pipe produced
					erpnext.pipes_work_order.material_inspection(frm, 'Quality Inspection');
				}, __("Create"));
			}

        }
    },
    stop_unstop: function(frm, status){
        frappe.confirm(
            'Are you sure you want to ' + status + ' this Work Order?',
            function(){
                frm.call({
                    method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.stop_unstop',
                    args: {
                        pipes_work_order: cur_frm.doc.name,
                        status : status
                    },
                    callback: function(r){
                        if (status == 'start'){
                            var alertmsg = 'Work Order started';
                            frappe.show_alert(alertmsg)
						    frm.reload_doc();
                        }
                        else if (status == 'stop'){
                            var alertmsg = 'Work Order stopped';
                            frappe.show_alert(alertmsg)
						    frm.reload_doc();
                        }
                        else{
                            var alertmsg = 'Work Order resumed';
                            frappe.show_alert(alertmsg)
						    frm.reload_doc();
                        }
                    }
                })
            }
        )
    },
    material_transfer: function(frm,cdt,cdn, status){
        var doc = cur_frm.doc;
        let batch_list_items = [];
		var j = 0;
		for (var i in doc.required_items){
			if (doc.required_items[i].status == "Not Transferred"){
				batch_list_items[j] = doc.required_items[i];
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
				//var args = d.get_values();
				let selected_batch = '';
				let selected_items = d.fields_dict.batch_list.grid.get_selected_children();
				if(selected_items.length == 0) {
					frappe.throw({message: 'Please select Item form Table', title: __('Message'), indicator:'blue'})
				}
				for(let i in selected_items){
					selected_batch += (selected_items[i].batch_no) + ',';
				}
				frm.call({
					method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.material_transfer",
					args: {
						pipes_work_order: frm.doc.name,
						selected_batch: selected_batch,
						status: status
					},
					callback: function(r) {
						frm.reload_doc();
					}
				});
				d.hide();
				frm.reload_doc();
				frappe.show_alert("Material Transferred")
			}
		});
		d.show();
    },
    material_manufacture: function(frm, status){
        var doc = cur_frm.doc;
        var total_produced_pipe_weight = doc.produced_qty*doc.weight;
        var total_scrap_weight = doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut;
        var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
        var maf_manufacturing = (doc.mtf_manufacturing - total_weight_produced).toFixed(2);
        var paf_manufacturing = Math.floor(maf_manufacturing/doc.weight);
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
					fieldtype: "Section Break"
				},
				{
					label: 'Pipe Quanity to Manufacture',
					fieldname: 'pipe_qty',
					fieldtype: 'Int',
					default: undefined
				},
				{
					fieldtype: "Column Break"
				},
				{
					label: 'Pipes that can be manufactured',
					fieldname: 'pipes_tcbm',
					fieldtype: 'Int',
					default: paf_manufacturing,
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
				frm.call({
					method: "pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.pipe_manufacture",
					args: {
						pipes_work_order: frm.doc.name,
						pipe_qty: values.pipe_qty,
						status: status
					},
					callback: function(r) {
						frm.reload_doc();
						var alertmsg = values.pipe_qty + " Pipes manufactured";
						frappe.show_alert(alertmsg);
					}
				})
			}
		});
		d.show();
	},
	material_scrap: function(frm,status){
		var doc = cur_frm.doc;
        var total_produced_pipe_weight = doc.produced_qty*doc.weight;
        var total_scrap_weight = doc.pipe_jala_bora + doc.phakra_pipe + doc.bari_end_cut;
        var total_weight_produced = total_produced_pipe_weight+total_scrap_weight;
		var maf_manufacturing = 0;
		for (var i in doc.required_items){
			if (doc.required_items[i].status=='Transferred'){
				maf_manufacturing += doc.required_items[i].batch_qty - doc.required_items[i].consumed_qty;
			}
		}
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
					default: maf_manufacturing
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
				if (total_scrap_tmp>maf_manufacturing){
					frappe.throw("Cannot Process Scrap Quanity greater than Remaining Raw Material");
				}
				d.hide();
				frm.call({
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
						frappe.show_alert(alertmsg);
					}
				})
			}
		});
		d.show();
	},
	material_inspection: function(frm, status){
		var doc = frm.doc;
		var total_processed_pipes = doc.no_of_a_quality_pipes+doc.no_of_b_quality_pipes;
		var pipes_to_be_processed = doc.produced_qty - total_processed_pipes;
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
					fieldtype: 'Int',
					default: pipes_to_be_processed,
					read_only: 1
				},
				{
					fieldtype: 'Section Break',
				},
				{
					label: 'No of A Quality Pipes',
					fieldname: 'pipe_a_qty',
					fieldtype: 'Int',
					default: 0
				},
				{
					fieldtype: 'Column Break',
				},
				{
					label: 'No of B Quality Pipes',
					fieldname: 'pipe_b_qty',
					fieldtype: 'Int',
					default: 0
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
				frm.call({
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
						frappe.show_alert(alertmsg);
					}
				});
			}
		});
		d.show();
	}
};