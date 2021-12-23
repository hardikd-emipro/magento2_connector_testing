#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Describes configuration for Magento Instance.
"""
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """
    Describes Magento Instance Configurations
    """
    _inherit = 'res.config.settings'

    magento_instance_id = fields.Many2one(
        'magento.instance', 'Instance', ondelete='cascade', help="This field relocates magento instance")
    magento_website_id = fields.Many2one('magento.website', string="Website", help="Magento Websites",
                                         domain="[('magento_instance_id', '=', magento_instance_id)]")
    magento_storeview_id = fields.Many2one('magento.storeview', string="Storeviews", help="Magento Storeviews",
                                           domain="[('magento_website_id', '=', magento_website_id)]")
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouses",
                                     help='Warehouses used to compute stock to update on Magento.')
    magento_website_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                                   help='Warehouse to be used to deliver an order from this website.')
    magento_website_pricelist_id = fields.Many2one('product.pricelist', string="Magento Pricelist",
                                                   help="Product price will be taken/set from this pricelist if Catalog Price Scope is website")
    magento_website_pricelist_ids = fields.Many2many('product.pricelist', string="Website Pricelists",
                                     help='Pricelists to set for Magento websites.')
    magento_team_id = fields.Many2one('crm.team', string='Sales Team', help="Sales Team")
    magento_sale_prefix = fields.Char(string="Sale Order Prefix",
                                      help="A prefix put before the name of imported sales orders.\n"
                                           "For example, if the prefix is 'mag-', the sales "
                                           "order 100000692 in Magento, will be named 'mag-100000692' in ERP.")

    magento_version = fields.Selection([('2.1', '2.1.*'), ('2.2', '2.2.*'), ('2.3', '2.3.*')],
                                       string="Magento Versions", help="Version of Magento Instance")
    magento_url = fields.Char(string='Magento URLs', help="URL of Magento")
    catalog_price_scope = fields.Selection([('global', 'Global'), ('website', 'Website')],
                                           string="Magento Catalog Price Scope", help="Scope of Price in Magento",
                                           default='global')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist",
                                   help="Product price will be taken/set from this pricelist if Catalog Price Scope is global")
    allow_import_image_of_products = fields.Boolean("Import Images of Products", default=False,
                                                    help="Import product images along with product from Magento while import product?")
    # Import Product Stock
    is_import_product_stock = fields.Boolean('Is Import Magento Product Stock?', default=False,
                                             help="Import Product Stock from Magento to Odoo")
    import_stock_warehouse = fields.Many2one('stock.warehouse', string="Import Product Stock Warehouse",
                                             help="Warehouse for import stock from Magento to Odoo")
    magento_stock_field = fields.Selection(
        [('free_qty', 'On Hand Quantity'), ('virtual_available', 'Forecast Quantity')],
        string="Magento Stock Type", default='free_qty', help="Magento Stock Type")
    auto_create_product = fields.Boolean(string="Auto Create Odoo Product", default=False,
                                         help="Checked True, if you want to create new product in Odoo if not found."
                                              "\nIf not checked, Job will be failed while import order or product..")
    company_id = fields.Many2one('res.company', string='Magento Company', help="Magento Company")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    is_use_odoo_order_sequence = fields.Boolean("Is Use Odoo Order Sequences?", default=False,
                                                help="If checked, Odoo Order Sequence is used")
    invoice_done_notify_customer = fields.Boolean(string="Invoices Done Notify customer", default=False,
                                                  help="while export invoice send email")
    is_multi_warehouse_in_magento = fields.Boolean(string="Is Multi Inventory Sources in Magento?", default=False,
                                                   help="If checked, Multi Inventory Sources used in Magento")

    import_magento_order_status_ids = fields.Many2many('import.magento.order.status',
                                                       'magento_config_settings_order_status_rel',
                                                       'magento_config_id', 'status_id', "Import Order Status",
                                                       help="Select order status in which you want to import the orders from Magento to Odoo.")
    import_order_after_date = fields.Datetime(
        help="Connector only imports those orders which have created after a given date.")
    import_product_category = fields.Many2one(
        'product.category',
        string="Import Product Category",
        help="While importing a product, "
             "the selected category will set in that product."
    )
    tax_calculation_method = fields.Selection([
        ('excluding_tax', 'Excluding Tax'), ('including_tax', 'Including Tax')],
        string="Tax Calculation Method into Magento Website", default="excluding_tax",
        help="This indicates whether product prices received from Magento is including tax or excluding tax,"
             " when import sale order from Magento"
    )
    magento_set_sales_description_in_product = fields.Boolean(
        string="Use Sales Description of Magento Product",
        config_parameter="odoo_magento2_ept.set_magento_sales_description",
        help="In both odoo products and Magento layer products, it is used to set the description and short description"
    )

    @api.onchange('magento_instance_id')
    def onchange_magento_instance_id(self):
        """
        Set default values for configuration when change/ select Magento Instance.
        """
        magento_instance_id = self.magento_instance_id
        if magento_instance_id:
            self.warehouse_ids = [
                (6, 0, magento_instance_id.warehouse_ids.ids)] if magento_instance_id.warehouse_ids else False
            self.magento_stock_field = magento_instance_id.magento_stock_field
            self.magento_version = magento_instance_id.magento_version
            self.auto_create_product = magento_instance_id.auto_create_product
            self.allow_import_image_of_products = magento_instance_id.allow_import_image_of_products
            self.catalog_price_scope = magento_instance_id.catalog_price_scope
            self.pricelist_id = magento_instance_id.pricelist_id.id if magento_instance_id.pricelist_id else False
            self.is_import_product_stock = magento_instance_id.is_import_product_stock
            self.import_stock_warehouse = magento_instance_id.import_stock_warehouse.id if \
                magento_instance_id.import_stock_warehouse else False
            self.is_multi_warehouse_in_magento = magento_instance_id.is_multi_warehouse_in_magento
            self.company_id = magento_instance_id.company_id.id if magento_instance_id.company_id else False
            # self.is_use_odoo_order_sequence = magento_instance_id.is_use_odoo_order_sequence
            self.import_product_category = magento_instance_id.import_product_category if magento_instance_id.import_product_category else False
            self.invoice_done_notify_customer = magento_instance_id.invoice_done_notify_customer
            self.import_magento_order_status_ids = magento_instance_id.import_magento_order_status_ids.ids
            self.import_order_after_date = magento_instance_id.import_order_after_date or False

    @api.onchange('magento_website_pricelist_ids')
    def onchange_magento_website_pricelist_ids(self):
        if self.magento_website_id:
            self.magento_website_id.write(
                {'pricelist_ids': [(6, 0, self.magento_website_pricelist_ids.ids)]})

    @api.onchange('magento_website_id')
    def onchange_magento_website_id(self):
        """
        set some Magento configurations based on changed Magento instance.
        """
        magento_website_id = self.magento_website_id
        self.magento_storeview_id = self.magento_website_warehouse_id = self.magento_website_pricelist_ids = False
        if magento_website_id:
            if magento_website_id.pricelist_ids.ids:
                self.magento_website_pricelist_ids = magento_website_id.pricelist_ids.ids
            if magento_website_id.warehouse_id:
                self.magento_website_warehouse_id = magento_website_id.warehouse_id.id
            self.tax_calculation_method = magento_website_id.tax_calculation_method

    @api.onchange('magento_storeview_id')
    def onchange_magento_storeview_id(self):
        """
        set some Magento configurations based on changed Magento instance.
        """
        magento_storeview_id = self.magento_storeview_id
        self.is_use_odoo_order_sequence = self.magento_team_id = False
        self.magento_sale_prefix = ''
        if magento_storeview_id:
            if magento_storeview_id.team_id:
                self.magento_team_id = magento_storeview_id.team_id.id
            self.magento_sale_prefix = magento_storeview_id.sale_prefix
            self.is_use_odoo_order_sequence = magento_storeview_id.is_use_odoo_order_sequence

    def execute(self):
        """
        Save all selected Magento Instance configurations
        """
        magento_instance_id = self.magento_instance_id
        res = super(ResConfigSettings, self).execute()
        if magento_instance_id:
            self.write_instance_vals(magento_instance_id)
        if self.magento_website_id:
            self.magento_website_id.write({
                'warehouse_id': self.magento_website_warehouse_id.id,
                'tax_calculation_method': self.tax_calculation_method,
            })
        if self.magento_storeview_id:
            self.magento_storeview_id.write({
                'team_id': self.magento_team_id,
                'sale_prefix': self.magento_sale_prefix,
                'is_use_odoo_order_sequence': self.is_use_odoo_order_sequence
            })
        return res

    def write_instance_vals(self, magento_instance_id):
        """
        Write values in the instance
        :param magento_instance_id: instance ID
        :return:
        """
        values = {}
        values.update({
            'warehouse_ids': [(6, 0, self.warehouse_ids.ids)] if self.warehouse_ids else False,
            'magento_stock_field': self.magento_stock_field,
            'auto_create_product': self.auto_create_product,
            'catalog_price_scope': magento_instance_id.catalog_price_scope if magento_instance_id else False,
            'allow_import_image_of_products': self.allow_import_image_of_products,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
            'is_import_product_stock': self.is_import_product_stock,
            'import_stock_warehouse': self.import_stock_warehouse.id if self.import_stock_warehouse else False,
            'invoice_done_notify_customer': self.invoice_done_notify_customer,
            'import_magento_order_status_ids': [(6, 0, self.import_magento_order_status_ids.ids)],
            'is_multi_warehouse_in_magento': self.is_multi_warehouse_in_magento if self.is_multi_warehouse_in_magento else False,
            'import_product_category': self.import_product_category if self.import_product_category else "",
            'import_order_after_date': self.import_order_after_date if self.import_order_after_date else "",
        })
        magento_instance_id.write(values)
