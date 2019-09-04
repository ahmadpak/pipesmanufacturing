var refresh_check = 0;
frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
		if (refresh_check == 0){
			frm.events.make_custom_buttons(frm);
		}
		
	},
	
	onload: function(){
		refresh_check = 0;
	},

    make_custom_buttons: function(frm) {
        if (frm.doc.docstatus == 1 && frm.doc.status != 'Stopped' ) {
			refresh_check = 1;
			var has_pipe = 0;
			var has_non_pipe = 0;
			var make_pwo_button = 0;  
			for (var i in cur_frm.doc.items){
				if (cur_frm.doc.items[i].item_code.includes("Pipe-MS",0)){
					has_pipe = 1;
					if (cur_frm.doc.items[i].ordered_qty!=cur_frm.doc.items[i].qty){
						make_pwo_button = 1;
					}
				}
				else{
					has_non_pipe = 1;
				}
			}
            if (flt(frm.doc.per_ordered, 2) < 100) {
                // make
                if (frm.doc.material_request_type === "Manufacture" && has_pipe == 1 && make_pwo_button == 1 && cur_frm.doc.pipes_work_order == undefined) {
					frm.add_custom_button(__("Pipes Work Order"),
						() => frm.events.raise_pipes_work_orders(frm), __('Create'));
				}
				if (has_non_pipe == 1){
					frm.add_custom_button(__("Work Order"),
					() => frm.events.raise_work_orders(frm), __('Create'));
				}
            }
        }
	},
	
    raise_pipes_work_orders: function(frm) {
		frappe.call({
			method:"pipesmanufacturing.pipes_manufacturing.utils.material_request.raise_pipes_work_orders",
			args: {
				"material_request": frm.doc.name
			},
			callback: function(r) {
				if(r) {
					frm.reload_doc();
				}
			}
		});
	},

	raise_work_orders: function(frm) {
		frappe.call({
			method:"erpnext.stock.doctype.material_request.material_request.raise_work_orders",
			args: {
				"material_request": frm.doc.name
			},
			callback: function(r) {
				if(r.message.length) {
					frm.reload_doc();
				}
			}
		});
	}
})
/*
frappe.ui.form.on("Material Request Item",{
	item_code: function(frm,cdt,cdn){
		var item = frappe.model.get_doc(cdt,cdn);
		if (cur_frm.doc.items.length!=1){
			for (var i=0; i< cur_frm.doc.items.length-1; i++){
				if (cur_frm.doc.items[i].item_code == item.item_code){
					frappe.throw("Item " + item.item_code + " is already added!")
				}
			}
		}
		
	}
})
*/