# -*- coding: utf-8 -*-
"""
Describes fields mapping to Magento products
"""
from datetime import datetime
from odoo import fields, models


class ProductProduct(models.Model):
    """
    Describes fields mapping to Magento products
    """
    _inherit = 'product.product'

    def view_magento_products(self):
        """
        This method is used to view Magento product.
        :return: Action
        """
        magento_product_ids = self.mapped('magento_product_ids')
        xmlid = ('odoo_magento2_ept', 'action_magento_stock_picking')
        action = self.env['ir.actions.act_window'].for_xml_id(*xmlid)
        action['domain'] = "[('id','in',%s)]" % magento_product_ids.ids
        if not magento_product_ids:
            return {'type': 'ir.actions.act_window_close'}
        return action

    magento_product_ids = fields.One2many(
        'magento.product.product',
        inverse_name='odoo_product_id',
        string='Magento Products',
        help='Magento Product Ids'
    )

    def write(self, vals):
        """
        This method will archive/unarchive Magento product based on Odoo Product
        :param vals: Dictionary of Values
        """
        if 'active' in vals.keys():
            magento_product_product_obj = self.env['magento.product.product']
            for product in self:
                magento_product = magento_product_product_obj.search(
                        [('odoo_product_id', '=', product.id)])
                if vals.get('active'):
                    magento_product = magento_product_product_obj.search(
                            [('odoo_product_id', '=', product.id), ('active', '=', False)])
                magento_product and magento_product.write({'active': vals.get('active')})
        res = super(ProductProduct, self).write(vals)
        return res
