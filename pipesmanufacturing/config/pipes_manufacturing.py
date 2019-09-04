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
                    "lable": _("Pipes Work Order"),
                    "description": _("Managing ERW pipe manufactuing"),
                    "onboard": 1,
                },

                {
                    "type": "doctype",
                    "name": "Strip Work Order",
                    "lable": _("Strip Work Order"),
                    "description": _("Managing HRC and CRC strip Work Order"),
                    "onboard": 1,
                }
        #        {
        #            "type": "doctype",
        #            "name": "Coil Work Order",
        #            "onboard": 1,
        #            "lable": _("Coil Work Order"),
        #            "description": _("Managing HRC and CRC coil Work Order"),
        #        }
        #    ],
        #    "label": ("Settings"),
        #    "items": [
        #        {
        #            "type": "doctype",
        #            "name": "Manufacturing Settings",
        #            "onboard": 1,
        #            "label": _("Manufacturing Settings"),
        #            "description": _("Settings for manufacturing"),
        #        }
            ]    
        }
    ]