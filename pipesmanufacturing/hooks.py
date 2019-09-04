# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "pipesmanufacturing"
app_title = "Pipes Manufacturing"
app_publisher = "Havenir"
app_description = "App for ERW pipe manufacturing process"
app_icon = "octicon octicon-project"
app_color = "grey"
app_email = "info@havenir.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/pipesmanufacturing/css/pipesmanufacturing.css"
# app_include_js = "/assets/pipesmanufacturing/js/pipesmanufacturing.js"

# include js, css files in header of web template
# web_include_css = "/assets/pipesmanufacturing/css/pipesmanufacturing.css"
# web_include_js = "/assets/pipesmanufacturing/js/pipesmanufacturing.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

fixtures = [{
    'dt': 'Custom Field', 'filters':[
        [
            'name', 'in', [
                "Material Request-pipes_work_order",
                "Stock Entry-pipes_work_order",
                "Stock Entry-strip_work_order",
                "Batch-batch_stock_status",
                "Batch-pipes_work_order",
                "Batch-strip_work_order",
                "Batch-allocated_quantity"
            ]
        ]
    ]
}]

doctype_js = {
    "Material Request" : "pipes_manufacturing/utils/material_request.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "pipesmanufacturing.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "pipesmanufacturing.install.before_install"
# after_install = "pipesmanufacturing.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "pipesmanufacturing.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

doc_events = {
    "Delivery Note":{
        "on_cancel"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status",
        "on_submit"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status"
    },
    "Purchase Receipt":{
        "on_cancel"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status",
        "on_submit"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status"
    },
    "Stock Entry":{
        "on_cancel"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status",
        "on_submit"  :   "pipesmanufacturing.pipes_manufacturing.utils.batch.update_bactch_stock_status"
    },
    'Material Request':{
        'validate'  :   'pipesmanufacturing.pipes_manufacturing.utils.material_request.verify_items'
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"pipesmanufacturing.tasks.all"
# 	],
# 	"daily": [
# 		"pipesmanufacturing.tasks.daily"
# 	],
# 	"hourly": [
# 		"pipesmanufacturing.tasks.hourly"
# 	],
# 	"weekly": [
# 		"pipesmanufacturing.tasks.weekly"
# 	]
# 	"monthly": [
# 		"pipesmanufacturing.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "pipesmanufacturing.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "pipesmanufacturing.event.get_events"
# }

