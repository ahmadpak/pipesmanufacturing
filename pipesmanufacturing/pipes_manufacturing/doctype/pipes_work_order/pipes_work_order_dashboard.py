from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'pipes_work_order',
		'transactions': [
			{
				'items': ['Stock Entry','Material Request']
			}
		]
	}