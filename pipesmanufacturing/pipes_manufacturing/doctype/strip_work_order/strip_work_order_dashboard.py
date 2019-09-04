from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'strip_work_order',
		'transactions': [
			{
				'items': ['Stock Entry']
			}
		]
	}