// Copyright (c) 2019, Havenir and contributors
// For license information, please see license.txt

// Function to at variables in string
function parse(str) {
    var args = [].slice.call(arguments, 1),
        i = 0;

    return str.replace(/%s/g, () => args[i++]);
}

frappe.ui.form.on('Strip Work Order', {
	
	setup: function(frm){
		frm.set_query('required_item',function(){
			return {
				filters: {
					'item_code': ['like','%Coil-MS%']
				}
			}
		});
	},

	refresh: function(frm){
		if (cur_frm.doc.docstatus==1){
			erpnext.strip_work_order.set_custom_buttons(frm);
		}
	},

	required_item: function(frm){
		var coil_item_code = cur_frm.doc.required_item;
		if (coil_item_code){
			frm.set_query('batch_no',function(){
				return{
					filters: {
						'item': ['like',coil_item_code],
						'batch_stock_status': ['like', 'Available']
					}
				}
			});
			frm.call({
				method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
					args: {
						item_code: coil_item_code,
						variant: 'Coil-MS'
					},
					callback: function(r){
						var coil_thickness = r.message.thickness;
						var coil_thickness_length = (coil_thickness.toString()).length;
						var str_pipe_thickness = parse('%%s',coil_thickness);;
						cur_frm.doc.coil_width = r.message.width;
						cur_frm.refresh_field('coil_width');

						//making pipe filters
						if(coil_thickness_length==1 || coil_thickness_length==2){
							str_pipe_thickness += '.00 MM%';
						}
						else if (coil_thickness_length==3){
							str_pipe_thickness += '0 MM%'
						}
						else{
							str_pipe_thickness += ' MM%'
						}
						frm.fields_dict.production_item.grid.get_field('pipe_item_code').get_query = function(){
							return {
								filters:{
									'item_code': ['like',str_pipe_thickness],
									'item_group': ['like','Pipes']
								}
							}
						}
					}
			})
		}
	},

	batch_no: function(frm){
		var doc = cur_frm.doc;
		if(doc.batch_no){
			frm.call({
				method: 'pipesmanufacturing.pipes_manufacturing.doctype.strip_work_order.strip_work_order.batch_qty',
				args: {
					batch_no : doc.batch_no,
					s_warehouse: doc.s_warehouse,
					required_item: doc.required_item
				},
				callback: function(r){
					doc.batch_qty = r.message;
					cur_frm.refresh_field('batch_qty')
				}
			})
		}
	},
	
	wip_warehouse: function(frm){
		var doc = cur_frm.doc;
		if (doc.s_warehouse == doc.wip_warehouse){
			doc.wip_warehouse = null;
			cur_frm.refresh_field('wip_warehouse')
			frappe.throw('Source and Work In Progress warehouses cannot be same!')
		}
	}
});

frappe.ui.form.on('Strip Work Order Item', {
	production_item_remove:function(frm){
		var doc = cur_frm.doc;
		var tmp_total_strips_weight = 0;
		var tmp_coil_side_cutting = 0;
		var tmp_scrap_percentage = 0;
		for (var i in doc.production_item){
			tmp_total_strips_weight += doc.production_item[i].total_strip_weight;
		}
		tmp_coil_side_cutting = (doc.allocate_quantity - tmp_total_strips_weight).toFixed(0);
		tmp_scrap_percentage = ((tmp_coil_side_cutting/doc.allocate_quantity)*100).toFixed(0);
		doc.total_strips_weight = tmp_total_strips_weight;
		doc.coil_side_cutting = tmp_coil_side_cutting;
		doc.scrap_percentage = tmp_scrap_percentage;
		cur_frm.refresh_field('total_strips_weight');
		cur_frm.refresh_field('coil_side_cutting');
		cur_frm.refresh_field('scrap_percentage');
	},

	pipe_item_code: function(frm,cdt,cdn){
		var production = frappe.model.get_doc(cdt,cdn);
		if(cur_frm.doc.required_item){
			if(production.pipe_item_code){
				frm.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.pipes_work_order.pipes_work_order.get_item_attributes',
					args: {
						item_code: production.pipe_item_code,
						variant: 'Pipe'
					},
					callback: function(r){
						var pipe_thickness = r.message.thickness;
						var pipe_width = r.message.width;
						var pipe_thickness_length = (pipe_thickness.toString()).length;
						
						//making strip name
						var strip_name = parse('Strip-MS-%s',pipe_width);
						strip_name += parse(' MM-%s',pipe_thickness);
						if(pipe_thickness_length==1 || pipe_thickness_length==2){
							strip_name += '.00 MM';
						}
						else if (pipe_thickness_length==3){
							strip_name += '0 MM'
						}
						else{
							strip_name += ' MM'
						}
						var tmp_strip_weight = (pipe_width/cur_frm.doc.coil_width)*cur_frm.doc.allocate_quantity;
						tmp_strip_weight = tmp_strip_weight.toFixed(0);
						if (production.qty == 0 || production.qty== null){
							frappe.model.set_value(cdt,cdn,'qty',1);
						}
						var tmp_total_strip_weight = tmp_strip_weight*production.qty;

						var tmp_parent_strips_weight = 0;		// Updating total strips weight value
						for(var i in cur_frm.doc.production_item){
							tmp_parent_strips_weight += cur_frm.doc.production_item[i].total_strip_weight;
						}
						
						var tmp_coil_side_cutting = (cur_frm.doc.allocate_quantity - tmp_parent_strips_weight).toFixed(0);
						
						var tmp_scrap_percentage = (tmp_coil_side_cutting/cur_frm.doc.allocate_quantity)*100;
						
						if (tmp_coil_side_cutting<0){
							frappe.throw("Cannot manufacture this many items");
						}

						cur_frm.doc.total_strips_weight = tmp_parent_strips_weight;
						cur_frm.doc.coil_side_cutting = tmp_coil_side_cutting;
						cur_frm.doc.scrap_percentage = tmp_scrap_percentage;
						cur_frm.refresh_field('total_strips_weight');
						cur_frm.refresh_field('coil_side_cutting');
						cur_frm.refresh_field('scrap_percentage');
						frappe.model.set_value(cdt,cdn,'strip_width',pipe_width);
						frappe.model.set_value(cdt,cdn,'strip_weight',tmp_strip_weight);
						frappe.model.set_value(cdt,cdn,'total_strip_weight',tmp_total_strip_weight);
						frappe.model.set_value(cdt,cdn,"strip_item_code",strip_name);
					}
				})
			}
			else{
				frappe.model.set_value(cdt,cdn, "strip_item_code", null);
			}
		}
		else{
			frappe.throw("Please enter Coil Item Code!")
		}
	},
	
	qty: function(frm,cdt,cdn){
		var production = frappe.model.get_doc(cdt,cdn);
		if(cur_frm.doc.required_item && production.qty!=0 && production.qty!=null){
			var tmp_total_strip_weight = production.strip_weight*production.qty;
			frappe.model.set_value(cdt,cdn,'total_strip_weight',tmp_total_strip_weight);
			
			var tmp_parent_strips_weight = 0;		// Updating total strips weight value
			for(var i in cur_frm.doc.production_item){
				tmp_parent_strips_weight += cur_frm.doc.production_item[i].total_strip_weight;
			}
			cur_frm.doc.total_strips_weight = tmp_parent_strips_weight;
			var tmp_coil_side_cutting = cur_frm.doc.allocate_quantity - tmp_parent_strips_weight;
			tmp_coil_side_cutting = tmp_coil_side_cutting.toFixed(0);
			cur_frm.doc.coil_side_cutting = tmp_coil_side_cutting;
			var tmp_scrap_percentage = (tmp_coil_side_cutting/cur_frm.doc.allocate_quantity)*100;
			cur_frm.doc.scrap_percentage = tmp_scrap_percentage;
			if (tmp_coil_side_cutting<0){
				frappe.throw("Cannot manufacture this many items");
			}
			cur_frm.refresh_field('total_strips_weight');
			cur_frm.refresh_field('coil_side_cutting');
			cur_frm.refresh_field('scrap_percentage');
		}
		else{
			frappe.model.set_value(cdt,cdn,'qty',null);	
		}
	}
});

erpnext.strip_work_order = {
	set_custom_buttons: function(frm){
		var doc = cur_frm.doc;
		if (doc.status == 'Not Started'){
			var btn1 = frm.add_custom_button(__('Start'), function() {
				erpnext.strip_work_order.start(frm);
			});
			btn1.addClass('btn-primary');
		}
		else if (doc.status != 'Stopped' && doc.status != 'Completed'){
			var btn1 = frm.add_custom_button(__('Stop'), function() {
				erpnext.strip_work_order.stop_upstop(frm,"Stopped");
			}, __("Status"));
		}
		else if (doc.status == 'Stopped'){
			var btn1 = frm.add_custom_button(__('Resume'), function() {
				erpnext.strip_work_order.stop_upstop(frm,"Resume");
			}, __("Status"));
		}
		if (doc.status == 'Started'){
			var btn1 = frm.add_custom_button(__('Material Trasnfer'), function() {
				erpnext.strip_work_order.update_stock(frm,"Material Transferred");
			});
			btn1.addClass('btn-primary');
		}
		else if (doc.status == 'In Process'){
			var btn1 = frm.add_custom_button(__('Manufacture'), function() {
				erpnext.strip_work_order.update_stock(frm,"Material Manufacture");
			});
			btn1.addClass('btn-primary');
		}
	},
	start: function(frm){
		frappe.confirm(
			'Are you sure you want to start this work order?',
			function(){
				frappe.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.strip_work_order.strip_work_order.start',
					args: {
						strip_work_order: frm.doc.name
					},
					callback: function(r){
						var alert_str = 'Strip Work Order# ' + frm.doc.name + ' started';
						frappe.show_alert(alert_str)
						frm.reload_doc();
					}
				})
			},
			
			function(){
				
			}
		)
	},
	stop_upstop: function(frm,status){
		var alert_str = '';
		var msg = '';
		if (status == 'Stopped'){
			alert_str = 'Strip Work Order# ' + frm.doc.name + ' stopped';
			msg = 'stop';
		}
		else{
			alert_str = 'Strip Work Order# ' + frm.doc.name + ' resumed';
			msg = 'resume';
		}
		frappe.confirm(
			'Are you sure you want to ' + msg + ' this work order?',
			function(){
				frappe.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.strip_work_order.strip_work_order.stop_unstop',
					args: {
						strip_work_order: frm.doc.name,
						status: status
					},
					callback: function(r){
						frappe.show_alert(alert_str)
						frm.reload_doc();
					}
				})
			},
			
			function(){
				
			}
		)
	},
	update_stock: function(frm,status){
		if (status == 'Material Transferred'){
			var alert_str = 'Material Transferred';
			var msg = 'trasnfer';
		}
		else{
			var alert_str = 'Products Manufactured';
			var msg = 'manufacture';
		}
		
		frappe.confirm(
			'Are you sure you want to ' + msg + ' items of this work order?',
			function(){
				frappe.call({
					method: 'pipesmanufacturing.pipes_manufacturing.doctype.strip_work_order.strip_work_order.update_stock',
					args: {
						strip_work_order: frm.doc.name,
						status: status
					},
					callback: function(r){
						frappe.show_alert(alert_str)
						frm.reload_doc();
					}
				})
			},
			
			function(){
				
			}
		)
	}
}