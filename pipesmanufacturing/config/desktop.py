from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Pipes Manufacturing",
			"category": "Modules",
			"label": _("Pipes Manufacturing"),
			"color": "blue",
			"icon": "octicon octicon-graph",
			"type": "domain",
			"description": "ERW Pipe Manufacturing Module",
			"onboard_present": 1
		}
	]
