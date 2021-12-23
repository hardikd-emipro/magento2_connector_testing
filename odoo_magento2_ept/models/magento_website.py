# -*- coding: utf-8 -*-
"""
Describes Methods for Magento Website.
"""
import ast
from odoo import models, fields


class MagentoWebsite(models.Model):
    """
    Describes Magento Website.
    """
    _name = 'magento.website'
    _description = 'Magento Website'
    _order = 'sort_order ASC, id ASC'

    name = fields.Char(string="Website Name", required=True, readonly=True, help="Website Name")
    code = fields.Char(string="Website Code", readonly=True, help="Website Code")
    sort_order = fields.Integer(
        string='Website Sort Order',
        readonly=True,
        help='Website Sort Order'
    )
    magento_instance_id = fields.Many2one(
        'magento.instance',
        'Instance',
        ondelete='cascade',
        help="This field relocates magento instance"
    )
    magento_website_id = fields.Char(string="Magento Website", help="Magento Website Id")
    magento_base_currency = fields.Many2one(
        'res.currency',
        readonly=True,
        help="Magento Website Base Currency"
    )
    import_partners_from_date = fields.Datetime(
        string='Last partner import date',
        help='Date when partner last imported'
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Pricelist",
        help="Product Price is set in selected Pricelist if Catalog Price Scope is Website"
    )
    pricelist_ids = fields.Many2many('product.pricelist', string="Website Pricelist",
                                     help="Product Price is set in selected "
                                          "Pricelist if Catalog Price Scope is Website")
    store_view_ids = fields.One2many(
        "magento.storeview",
        inverse_name="magento_website_id",
        string='Magento Store Views',
        help='This relocates Magento Store Views'
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        help='Warehouse to be used to deliver an order from this website.'
    )
    company_id = fields.Many2one(
        'res.company',
        related='magento_instance_id.company_id',
        string='Company',
        readonly=True,
        help="Magento Company"
    )
    currency_id = fields.Many2one(
        "res.currency",
        related='pricelist_id.currency_id',
        readonly=True,
        help="Currency"
    )
    active = fields.Boolean(string="Status", default=True)
    global_channel_id = fields.Many2one(
        'global.channel.ept',
        string="Global Channel",
        help="Global Channel"
    )

    sale_order_count = fields.Integer(
        compute='_compute_orders_invoices_count',
        string="Total Sales Orders"
    )
    sale_quotations_count = fields.Integer(
        compute='_compute_orders_invoices_count',
        string="Total Sales Quotations"
    )
    invoice_count = fields.Integer(
        compute='_compute_orders_invoices_count',
        string="Total Invoices"
    )
    delivery_order_count = fields.Integer(
        compute='_compute_orders_invoices_count',
        string="Total Delivery Orders"
    )
    tax_calculation_method = fields.Selection([
        ('excluding_tax', 'Excluding Tax'), ('including_tax', 'Including Tax')],
        string="Tax Calculation Method into Magento Website", default="excluding_tax",
        help="This indicates whether product prices received from Magento is including tax or excluding tax,"
             " when import sale order from Magento"
    )
    refund_count = fields.Integer(
        compute='_compute_orders_invoices_count',
        string="Total Refunds"
    )

    def order_count_dashboard(self,instance_id,website_id):
        self._cr.execute(
            "SELECT count(*) AS row_count FROM sale_order WHERE "
            "state not in ('draft','sent','cancel') and magento_instance_id = %s "
            "and magento_website_id = %s "  % (instance_id, website_id))
        return self._cr.fetchall()[0][0]

    def quotations_count_dashboard(self,instance_id,website_id):
        self._cr.execute(
            "SELECT count(*) AS row_count FROM sale_order WHERE "
            "state in ('draft','sent','cancel') and magento_instance_id = %s "
            "and magento_website_id = %s" % (instance_id, website_id))
        return self._cr.fetchall()[0][0]

    def invoice_count_for_dashboard(self,instance_id,website_id):
        self._cr.execute("select count(distinct account_move.id) AS row_count "
                         "from sale_order_line_invoice_rel "
                         "inner join sale_order_line on "
                         "sale_order_line.id=sale_order_line_invoice_rel.order_line_id "
                         "inner join sale_order on sale_order.id=sale_order_line.order_id "
                         "inner join account_move_line on "
                         "account_move_line.id=sale_order_line_invoice_rel.invoice_line_id "
                         "inner join account_move on account_move.id=account_move_line.move_id "
                         "where sale_order.magento_website_id=%s "
                         "and sale_order.magento_instance_id=%s "
                         "and account_move.state in ('draft','posted') "
                         "and account_move.type in ('out_invoice','out_refund')" % (website_id, instance_id))
        return self._cr.fetchall()[0][0]

    def refund_count_for_dashboard(self, instance_id, website_id):
        query = """
                SELECT count(DISTINCT(r.id)) 
                    FROM account_move AS r
                        JOIN account_move_line AS rl
                            ON r.id = rl.move_id
                        JOIN sale_order_line_invoice_rel AS rel
                            ON rel.invoice_line_id = rl.id
                        JOIN sale_order_line AS sl
                            ON rel.order_line_id = sl.id
                        JOIN sale_order AS so
                            ON so.id = sl.order_id
                        JOIN magento_instance AS mi
                            ON mi.id = so.magento_instance_id
                        JOIN magento_website AS mw
                            ON mw.magento_instance_id = mi.id
                    WHERE r.type = 'out_refund'
                        AND mi.id = {}
                        AND mw.id = {}
                        AND r.state in {}
                """.format(website_id, instance_id, ('draft', 'posted', 'cancel'))
        self._cr.execute(query)
        return self._cr.fetchall()[0][0]

    def delivery_count_dashboard(self,instance_id,website_id):
        self._cr.execute(
            "SELECT count(*) AS row_count FROM stock_picking as SP "
            "inner join sale_order as SO on SP.sale_id = SO.id "
            "inner join stock_location as SL on SL.id = SP.location_dest_id "
            "WHERE SP.magento_instance_id = %s "
            "and SO.magento_website_id = %s"
            "and SL.usage = 'customer'" %
            (instance_id, website_id))
        return self._cr.fetchall()[0][0]

    def _compute_orders_invoices_count(self):
        """
        Count Orders and Invoices via sql query from database
        because of increase speed of Dashboard.
        :return:
        """
        for website in self:
            instance_id = website.magento_instance_id.id
            order_count = self.order_count_dashboard(instance_id,website.id)
            quotations_count = self.quotations_count_dashboard(instance_id, website.id)
            invoice_count = self.invoice_count_for_dashboard(instance_id, website.id)
            delivery_count = self.delivery_count_dashboard(instance_id, website.id)
            refund_count = self.refund_count_for_dashboard(instance_id, website.id)
            website.write({
                'sale_order_count' : order_count,
                'sale_quotations_count' : quotations_count,
                'invoice_count' : invoice_count,
                'delivery_order_count' : delivery_count,
                'refund_count': refund_count
            })

    def open_store_views(self):
        """
        This method used to view all store views for website.
        """
        form_view_id = self.env.ref('odoo_magento2_ept.view_magento_storeview_form').id
        tree_view = self.env.ref('odoo_magento2_ept.view_magento_storeview_tree').id
        action = {
            'name': 'Magento Store Views',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.storeview',
            'views': [(tree_view, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [('id', 'in', self.store_view_ids.ids)]
        }
        return action

    def get_all_operation_wizard(self):
        """
        This method uses for perform all operation from wizard .
        :return: Wizard
        """
        action = self._get_action('odoo_magento2_ept.action_wizard_magento_import_export_operation')
        action.update(
            {'context': {'default_magento_instance_ids': self.magento_instance_id.ids}})
        return action

    def get_magento_storeviews(self):
        """
        Get View of Magento Store View.
        :return:
        """
        return self._get_action('odoo_magento2_ept.action_magento_storeview')

    def get_magento_instance_id(self):
        """
        Get View of Magento Instances.
        :return:
        """
        return self._get_action('odoo_magento2_ept.action_magento_instance')

    def get_magento_config_settings(self):
        """
        Get View of Magento Configuration Settings.
        :return:
        """
        return self._get_action('odoo_magento2_ept.action_magento_config_settings')

    def get_action_magento_sales_quotations(self):
        """
        Get action for Magento Sale quotations
        """
        return self._get_action('odoo_magento2_ept.magento_action_sales_quotations_ept')

    def get_action_magento_sales_orders(self):
        """
        Get action for Magento Sale orders
        """
        return self._get_action('odoo_magento2_ept.magento_action_sales_order_ept')

    def get_action_delivery_orders(self):
        """
        Get action for Magento delivery orders
        """
        return self._get_action('odoo_magento2_ept.action_magento_stock_picking_tree_ept')

    def get_action_invoice_magento_invoices(self):
        """
        Get action for Magento invoices
        """
        return self._get_action('odoo_magento2_ept.action_magento_invoice_tree1_ept')

    def get_action_refund_magento_invoices(self):
        """
        Get action for Magento refunds
        """
        return self._get_action('odoo_magento2_ept.action_magento_refund_invoice_tree_ept')

    def _get_action(self, action):
        """
        Redirect to specific view.
        :param action: Action to open specific view
        :return:
        """
        action = self.env.ref(action) or False
        result = action.read()[0] or {}
        domain = []
        if result.get('domain'):
            domain = ast.literal_eval(result.get('domain'))
        if action.res_model in ['magento.storeview', 'sale.order']:
            domain.append(('magento_website_id', '=', self.id))
        if action.res_model in ['stock.picking']:
            domain.append(('sale_id.magento_website_id', '=', self.id))
        if action.res_model in ['account.move']:
            domain.append(('invoice_line_ids.sale_line_ids.order_id.magento_website_id', '=', self.id))

        if action.res_model in ['magento.instance']:
            domain.append(('website_ids.id', '=', self.id))
        if action.res_model in ['res.config.settings']:
            context = []
            if result.get('context'):
                context = ast.literal_eval(result.get('context'))
            context.update({'default_magento_instance_id': self.magento_instance_id.id})
            result['context'] = context
        result['domain'] = domain
        return result
