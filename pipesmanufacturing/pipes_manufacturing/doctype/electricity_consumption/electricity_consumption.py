# -*- coding: utf-8 -*-
# Copyright (c) 2020, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class ElectricityConsumption(Document):
    def on_submit(self):
        check_for_duplicate_dates(self)
        check_for_already_created_record(self)


def check_for_duplicate_dates(self):
    throw_error = 0
    for i in range(len(self.details)):
        if self.details[i].date > self.posting_date:
            frappe.throw('Cannot post for future dates at row: {}'.format(i+1))
        for j in range(len(self.details)):
            if (i == j):
                pass
            else:
                if (self.details[i].date == self.details[j].date):
                    frappe.msgprint(
                        "Duplicate entry of date at row {}".format(i+1))
                    throw_error = 1
    if throw_error == 1:
        frappe.throw('Please remove duplicate date entries')


def check_for_already_created_record(self):
    i = 0
    for entry in self.details:
        doc = frappe.get_list('Electricity Consumption Details', filters={
            'date': entry.date
        }, fields={
            'parent'
        })
        if(doc):
            frappe.throw('Data for date at row: {0}, already created in Doc: {1}'.format(i+1,doc[0].parent))
        i += 1