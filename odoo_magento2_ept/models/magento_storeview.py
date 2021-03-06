# -*- coding: utf-8 -*-
"""
Describes Magento Store View
"""
from odoo import models, fields


class MagentoStoreview(models.Model):
    """
    Describes Magento Store View
    """
    _name = 'magento.storeview'
    _description = "Magento Storeview"
    _order = 'sort_order ASC, id ASC'

    name = fields.Char(string="Store view Name", required=True, readonly=True, help="Store view Name")
    code = fields.Char(string="Store view Code", readonly=True, help="Store view Code")
    sort_order = fields.Integer(string='Website Sort Order', readonly=True, help='Website Sort Order')
    magento_website_id = fields.Many2one('magento.website', string="Website",
                                         help="This field relocates Magento Website")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language Name")
    team_id = fields.Many2one('crm.team', string='Sales Team', help="Sales Team")
    magento_storeview__id = fields.Char(string="Magento Store View", help="Magento Store View")
    magento_instance_id = fields.Many2one('magento.instance', related='magento_website_id.magento_instance_id',
                                          string='Instance', store=True, readonly=True, required=False, ondelete='cascade',
                                          help="This field relocates magento instance")
    import_orders_from_date = fields.Datetime(string='Import sale orders from date',
                                              help='Do not consider non-imported sale orders before this date. '
                                                   'Leave empty to import all sale orders')
    no_sales_order_sync = fields.Boolean(string='No Sales Order Synchronization',
                                         help='Check if the store view is active in Magento '
                                              'but its sales orders should not be imported.',
                                         )
    base_media_url = fields.Char(string='Base Media URL', help="URL for Image store at Magento.")
    active = fields.Boolean(string="Status", default=True)
    sale_prefix = fields.Char(string="Sale Order Prefix",
                              help="A prefix put before the name of imported sales orders.\n"
                                   "For example, if the prefix is 'mag-', the sales "
                                   "order 100000692 in Magento, will be named 'mag-100000692' in ERP.")
    is_use_odoo_order_sequence = fields.Boolean("Is Use Odoo Order Sequences?", default=False,
                                                help="If checked, Odoo Order Sequence is used")
