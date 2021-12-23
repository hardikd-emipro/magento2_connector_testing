# -*- coding: utf-8 -*-
"""
Describes fields for importing magento order status
"""
from odoo import models, fields


class ImportMagentoOrderStatus(models.Model):
    """
    Describes fields for importing magento order status
    """
    _name = "import.magento.order.status"
    _description = 'Order Status'

    name = fields.Char("Name")
    status = fields.Char("Status")
