from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
    return[
        {
			
            "label": _("Work Order"),
            "icon": "octicon octicon-project",
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
                },
            ]    
        }
    ]