# -*- coding: utf-8 -*-
"""
Describes fields mapping to Magento products templates
"""
from odoo import models, fields


class ProductTemplate(models.Model):
    """
    Describes fields mapping to Magento products templates
    """
    _inherit = 'product.template'

    magento_product_template_ids = fields.One2many(
        'magento.product.template',
        inverse_name='odoo_product_template_id',
        string='Magento Products Templates',
        help='Magento Product Template Ids'
    )

    def write(self, vals):
        """
        This method will archive/unarchive Magento product template based on Odoo Product template
        :param vals: Dictionary of Values
        """
        if 'active' in vals.keys():
            magento_product_template_obj = self.env['magento.product.template']
            for template in self:
                magento_templates = magento_product_template_obj.search(
                        [('odoo_product_template_id', '=', template.id)])
                if vals.get('active'):
                    magento_templates = magento_product_template_obj.search([
                        ('odoo_product_template_id', '=', template.id), ('active', '=', False)])
                magento_templates and magento_templates.write({'active': vals.get('active')})
        res = super(ProductTemplate, self).write(vals)
        return res
