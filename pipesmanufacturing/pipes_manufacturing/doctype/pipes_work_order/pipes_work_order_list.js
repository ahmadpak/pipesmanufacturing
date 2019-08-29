frappe.listview_settings['Pipes Work Order'] = {
    add_fields: ["status", "produciton_item", "weight", "qty","produced_qty", "planned_start_date", "expected_delivery_date"],
    filters: [["status", "!=", "Stopped"]],
	get_indicator: function(doc) {
		if(doc.status==="Submitted") {
			return [__("Not Started"), "orange", "status,=,Submitted"];
		} else {
			return [__(doc.status), {
				"Draft": "red",
				"Stopped": "red",
				"Not Started": "darkgrey",
				"Started" : "blue",
				"Material Partially Transfered" : "yellow",
				"In Process": "black",
				"Quality Inspection": "orange",
				"Completed": "green",
				"Cancelled": "red"
			}[doc.status], "status,=," + doc.status];
		}
	}//*/
};