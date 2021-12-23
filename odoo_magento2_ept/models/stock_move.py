#!/usr/bin/python3
"""
Describes methods for stock move.
"""
from odoo import models


class StockMove(models.Model):
    """
    Describes Magento order stock picking values
    """
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        """
        We need this method to set our custom fields in Stock Picking
        :return:
        """
        res = super(StockMove, self)._get_new_picking_values()
        sale_line_id = self.sale_line_id
        if sale_line_id and sale_line_id.order_id and sale_line_id.order_id.magento_instance_id:
            sale_order = sale_line_id.order_id
            if sale_order.magento_instance_id:
                res.update({
                    'magento_instance_id': sale_order.magento_instance_id.id,
                    'is_exported_to_magento': False,
                    'is_magento_picking': True
                })
                if sale_order.magento_instance_id.is_multi_warehouse_in_magento:
                    inv_loc = self.env['magento.inventory.locations'].search([
                        ('ship_from_location', '=', res.get('location_id')),
                        ('magento_instance_id', '=', sale_order.magento_instance_id.id)
                    ])
                    if inv_loc:
                        res.update({'magento_inventory_source': inv_loc.id})
        return res
