from __future__ import unicode_literals
import frappe
from frappe import _


def get_data():
    return[
        {
            "label": _("Work Order"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Pipes Work Order",
                    "label": _("Pipes Work Order"),
                    "description": _("Managing ERW pipe manufacturing"),
                    "onboard": 1,
                },

                {
                    "type": "doctype",
                    "name": "Strip Work Order",
                    "label": _("Strip Work Order"),
                    "description": _("Managing HRC and CRC strip Work Order"),
                    "onboard": 1,
                },
            ]
        },
        {
            "label": _("Electricity"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Electricity Consumption",
                    "label": _("Electricity Consumption"),
                    "description": _("For recording electricity units on daily basis"),
                    "onboard": 1
                }
            ]
        }
    ]
