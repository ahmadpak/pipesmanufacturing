frappe.listview_settings['Strip Work Order'] = {
    add_fields: ["status", "required_item", "batch_qty", "allocate_qty","total_strips_weight", "coil_side_cutting", "scrap_percentage"],
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
				"In Process": "yellow",
				"Completed": "green",
				"Cancelled": "red"
			}[doc.status], "status,=," + doc.status];
		}
	}//*/
};