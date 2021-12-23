# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

# mapping invoice type to journal type


class SaleWorkflowProcessEpt(models.Model):
    _inherit = "sale.workflow.process.ept"

    magento_order_type = fields.Many2one(
        'import.magento.order.status',
        string='Magento Order Status',
        help="Select order status for that you want to create auto workflow.")

