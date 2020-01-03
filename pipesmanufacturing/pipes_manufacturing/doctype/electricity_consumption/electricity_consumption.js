// Copyright (c) 2020, Havenir and contributors
// For license information, please see license.txt

frappe.ui.form.on("Electricity Consumption Details", {
  e_kva_units: function(frm, cdt, cdn) {
    var doc = frappe.get_doc(cdt, cdn);
    if (doc.e_kva_units < doc.m_kva_units) {
      doc.e_kva_units = "";
      frappe.throw(
        "KVA Units (Evening) must be greater of equal to KVA Units (Morning)"
      );
    }
  },
  e_kw_units: function(frm, cdt, cdn) {
    var doc = frappe.get_doc(cdt, cdn);
    if (doc.e_kw_units < doc.m_kw_units) {
      doc.e_kw_units = "";
      frappe.throw(
        "KW Units (Evening) must be greater of equal to KW Units (Morning)"
      );
    }
  }
});
