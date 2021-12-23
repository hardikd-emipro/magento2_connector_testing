# -*- coding: utf-8 -*-
"""
Describes methods for Magento Instance
"""
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.addons.odoo_magento2_ept.models.api_request import req
from odoo.exceptions import UserError, Warning
from odoo.tools import ustr


class MagentoInstance(models.Model):
    """
    Describes methods for Magento Instance
    """
    _name = 'magento.instance'
    _description = 'Magento Instance'

    @api.model
    def _default_set_import_product_category(self):
        return self.env.ref('product.product_category_all').id \
            if self.env.ref('product.product_category_all') else False

    @api.model
    def _default_order_status(self):
        """
        Get default status for importing magento order.
        :return:
        """
        order_status = self.env.ref('odoo_magento2_ept.pending')
        return [(6, 0, [order_status.id])] if order_status else False

    @api.model
    def set_magento_import_after_date(self):
        """ It is used to set after order date which has already created an instance.
        """
        sale_order_obj = self.env["sale.order"]
        instances = self.search([])
        order_after_date = datetime.now() - timedelta(30)
        for instance in instances:
            if not instance.import_order_after_date:
                order = sale_order_obj.search([('magento_instance_id', '=', instance.id)],
                                              order='date_order asc', limit=1) or False
                if order:
                    order_after_date = order.date_order
                else:
                    order_after_date = datetime.now() - timedelta(30)
                instance.write({"import_order_after_date": order_after_date})
        return order_after_date

    name = fields.Char("Instance Name", required=True)
    magento_version = fields.Selection([
        ('2.1', '2.1.*'),
        ('2.2', '2.2.*'),
        ('2.3', '2.3.*')
    ], string="Magento Versions", required=True, help="Version of Magento Instance")
    magento_url = fields.Char(string='Magento URLs', required=True, help="URL of Magento")
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string="Warehouses",
        required=True,
        help='Warehouses used to compute the stock quantities.'
             'If Warehouses is not selected then it is taken from Website'
    )
    website_ids = fields.One2many(
        'magento.website',
        'magento_instance_id',
        string='Website',
        readonly=True,
        help="Magento Websites"
    )
    lang_id = fields.Many2one('res.lang', string='Default Language', help="If a default language is selected, "
             "the records will be imported in the translation of this language.\n"
             "Note that a similar configuration exists for each storeview.")
    magento_stock_field = fields.Selection([('free_qty', 'On Hand Quantity'),('virtual_available', 'Forcast Quantity')],
                                           string="Magento Stock Type", default='free_qty', help="Magento Stock Type")
    catalog_price_scope = fields.Selection([('global', 'Global'),('website', 'Website')], string="Catalog Price Scopes",
                                           help="Scope of Price in Magento", default='global')
    pricelist_id = fields.Many2one('product.pricelist',string="Pricelist",
                                   help="Product Price is set in selected Pricelist")
    access_token = fields.Char(string="Magento Access Token", help="Magento Access Token")
    auto_create_product = fields.Boolean(string="Auto Create Magento Product", default=True,
                                         help="Checked True, if you want to create new product in Odoo if not found. "
                                              "\nIf not checked, Job will be failed while import order or product..")
    allow_import_image_of_products = fields.Boolean("Import Images of Products", default=False,
                                                    help="Import product images along with product from Magento while import product?")
    last_product_import_date = fields.Datetime(string='Last Import Products date', help="Last Import Products date")
    last_order_import_date = fields.Datetime(string="Last Orders import date", help="Last Orders import date")
    last_order_status_update_date = fields.Datetime(string="Last Shipment Export date", help="Last Shipment Export date")
    last_partner_import_date = fields.Datetime(string="Last Partner import date", help="Last Partner import date")
    last_update_stock_time = fields.Datetime(string="Last Update Product Stock Time", help="Last Update Stock Time")
    # Import Product Stock
    is_import_product_stock = fields.Boolean('Is Import Magento Product Stock?', default=False,
                                             help="Import Product Stock from Magento to Odoo")
    import_stock_warehouse = fields.Many2one('stock.warehouse', string="Import Product Stock Warehouse",
                                             help="Warehouse for import stock from Magento to Odoo")
    active = fields.Boolean(string="Status", default=True)
    company_id = fields.Many2one('res.company', string='Magento Company', help="Magento Company")
    # is_use_odoo_order_sequence = fields.Boolean(
    #     "Is Use Odoo Order Sequences?",
    #     default=False,
    #     help="If checked, Odoo Order Sequence is used"
    # )
    invoice_done_notify_customer = fields.Boolean(string="Invoices Done Notify customer", default=False,
                                                  help="while export invoice send email")
    is_multi_warehouse_in_magento = fields.Boolean(string="Is Multi Warehouse in Magento?", default=False,
                                                   help="If checked, Multi Warehouse used in Magento")
    # Require filed for cron
    auto_import_sale_orders = fields.Boolean("Auto Import Sale Orders?", default=False,
                                             help="This Field relocate auto import sale orders.")
    auto_import_product = fields.Boolean(string='Auto import product?', help="Auto Automatic Import Product")
    auto_export_product_stock = fields.Boolean(string='Auto Export Product Stock?', help="Automatic Export Product Stock")
    auto_export_invoice = fields.Boolean(string='Auto Export Invoice?', help="Auto Automatic Export Invoice")
    auto_export_shipment_order_status = fields.Boolean(string='Auto Export Shipment Information?',
                                                       help="Automatic Export Shipment Information")
    payment_method_ids = fields.One2many("magento.payment.method", "magento_instance_id", help="Payment Methods for Magento")
    shipping_method_ids = fields.One2many("magento.delivery.carrier", "magento_instance_id", help="Shipping Methods for Magento")
    import_magento_order_status_ids = fields.Many2many('import.magento.order.status', 'magento_instance_order_status_rel',
                                                       'magento_instance_id', 'order_status_id', "Import Order Status",
                                                       default=_default_order_status,
                                                       help="Select order status in which you want to import the orders from Magento to Odoo.")

    magento_import_product_page_count = fields.Integer(string="Magento Import Products Page Count", default=1,
                                                       help="It will fetch products of Magento from given page numbers.")
    magento_import_customer_page_count= fields.Integer(string="Magento Import Customers Page Count", default=1,
                                                       help="It will fetch Customers from Magento as per given page numbers.")
    magento_import_stock_min_qty = fields.Integer(string="Import Stock Minimum Quantity", default=999999999,
                                                  help="This purpose of this field is define import stock less than the field value,"
                                                       "Used as technical field.")
    magento_import_stock_scope_id = fields.Integer(string="Stock Import Scope", default=0,
                                                  help="This purpose of this field is define scope for import scope,"
                                                       "Used as technical field.")
    magento_import_order_page_count = fields.Integer(string="Magento Import order Page Count",
                                                     default=1,
                                                     help="It will fetch order of Magento from given page numbers.")
    active = fields.Boolean("Active", default=True)
    import_order_after_date = fields.Datetime(help="Connector only imports those orders which"
                                                   " have created after a "
                                                   "given date.",
                                              default=set_magento_import_after_date)
    import_product_category = fields.Many2one(
        'product.category',
        string="Import Product Categories",
        default=_default_set_import_product_category,
        help="While importing a product, "
             "the selected category will set in that product."
    )
    magento_verify_ssl = fields.Boolean(
        string="Verify SSL", default=False,
        help="Check this if your Magento site is using SSL certificate")

    _sql_constraints = [('unique_magento_host', 'unique(magento_url, access_token)',
                         "Instance already exists for given host. Host or Access Token must be Unique for the instance!")]

    def _compute_get_scheduler_list(self):
        seller_cron = self.env['ir.cron'].search([('magento_instance_id', '=', self.id)])
        for record in self:
            record.cron_count = len(seller_cron.ids)

    cron_count = fields.Integer(
        string="Scheduler Count",
        compute="_compute_get_scheduler_list",
        help="This Field relocates Scheduler Count."
    )

    def toggle_active(self):
        """
        This method is overridden for archiving other properties, while archiving the instance from the Action menu.
        """
        context = dict(self._context)
        context.update({'active_ids': self.ids})
        action = self[0].with_context(context).magento_action_open_deactive_wizard() if self else False
        return action

    def magento_action_open_deactive_wizard(self):
        """
        This method is used to open a wizard to display the information related to how many data active/inactive
        while instance Active/Inactive.
        :return: action
        """
        view = self.env.ref('odoo_magento2_ept.view_inactive_magento_instance')
        return {
            'name': _('Instance Active/Inactive Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'magento.queue.process.ept',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self._context,
        }

    def magento_action_archive_unarchive(self):
        """
        Archive/ Active related products, payment methods, websites, and storeviews of instance.
        """
        domain = [("magento_instance_id", "=", self.id)]
        ir_cron_obj = self.env["ir.cron"]
        magento_template_obj = self.env["magento.product.template"]
        magento_payment_method_obj = self.env["magento.payment.method"]
        magento_inventory_location_obj = self.env["magento.inventory.locations"]
        magento_website_obj = self.env['magento.website']
        magento_storeview_obj = self.env['magento.storeview']
        if self.active:
            activate = {"active": False}
            auto_crons = ir_cron_obj.search([("name", "ilike", self.name), ("active", "=", True)])
            if auto_crons:
                auto_crons.write(activate)
            magento_website_obj.search(domain).write(activate)
            magento_storeview_obj.search(domain).write(activate)
            magento_inventory_location_obj.search(domain).write(activate)
            magento_payment_method_obj.search(domain).write(activate)
        else:
            activate = {"active": True}
            domain.append(("active", "=", False))
            magento_website_obj.search(domain).write(activate)
            magento_storeview_obj.search(domain).write(activate)
            magento_inventory_location_obj.search(domain).write(activate)
            magento_payment_method_obj.search(domain).write(activate)
            # self.synchronize_metadata()
        self.write(activate)
        magento_template_obj.search(domain).write(activate)

        return True

    def list_of_instance_cron(self):
        """
        Opens view for cron scheduler of instance
        :return:
        """
        instance_cron = self.env['ir.cron'].search([('magento_instance_id', '=', self.id)])
        action = {
            'domain': "[('id', 'in', " + str(instance_cron.ids) + " )]",
            'name': 'Cron Scheduler',
            'view_mode': 'tree,form',
            'res_model': 'ir.cron',
            'type': 'ir.actions.act_window',
        }
        return action

    def cron_configuration_action(self):
        """
        Return action for cron configuration
        :return:
        """
        action = self.env.ref(
            'odoo_magento2_ept.action_magento_wizard_cron_configuration_ept'
        ).read()[0]
        context = {
            'magento_instance_id': self.id
        }
        action['context'] = context
        return action

    def _check_location_url(self, location_url):
        """
        Set Magento rest API URL
        :param location_url: Magento URL
        :return:
        """
        if location_url:
            location_url = location_url.strip()
            location_url = location_url.rstrip('/')
            location_vals = location_url.split('/')
            if location_vals[-1] != 'rest':
                location_url = location_url + '/rest'
        return location_url

    def test_connection(self):
        """
        This method check connection in magento.
        """
        self.ensure_one()
        try:
            api_url = "/V1/store/websites"
            website_response = req(self, api_url, method='GET')
        except Exception as error:
            raise UserError(_("Connection Test Failed! Here is what we got instead:\n \n%s" % ustr(error)))
        if website_response:
            raise UserError(_("Connection Test Succeeded! Everything seems properly set up!"))

    def synchronize_metadata(self):
        """
        Sync all the websites, store view , Payment methods and delivery methods
        """
        for record in self:
            record.sync_attribute_scope()
            # mage_website_ids = record.sync_website()
            record.sync_website()
            record.import_currency()
            record.sync_storeview()
            record.import_payment_method()
            record.import_delivery_method()
            record.import_magento_inventory_locations()
            self.env['magento.financial.status.ept'].create_financial_status(record, 'not_paid')

    def sync_attribute_scope(self):
        api_url = "/V1/products/attributes/price"
        try:
            response = req(self, api_url, method='GET')
        except Exception as error:
            raise error
        if response:
            self.catalog_price_scope = response.get("scope")

    def sync_website(self):
        """
        Sync all the websites from magento
        """
        magento_website_obj = self.env['magento.website']
        # mage_website_ids = []
        api_url = "/V1/store/websites"
        try:
            website_response = req(self, api_url, method='GET')
        except Exception as error:
            raise error
        for data in website_response:
            magento_website_id = data.get('id')
            code = data.get('code')
            name = data.get('name')
            if magento_website_id != 0:
                mage_website_id = self.website_ids.filtered(
                    lambda x: x.magento_website_id == str(magento_website_id)
                )
                if not mage_website_id:
                    mage_website_id = magento_website_obj.create({
                        'name': name,
                        'code': code,
                        'magento_website_id': magento_website_id,
                        'magento_instance_id': self.id
                    })
                # mage_website_ids.append(mage_website_id)
        # return mage_website_ids

    def open_all_websites(self):
        """
        This method used for smart button for view all website.
        return : Action.
        """
        form_view_id = self.env.ref('odoo_magento2_ept.view_magento_website_form').id
        tree_view = self.env.ref('odoo_magento2_ept.view_magento_website_tree').id
        action = {
            'name': 'Magento Website',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.website',
            'views': [(tree_view, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [('id', 'in', self.website_ids.ids)]
        }
        return action

    def sync_storeview(self):
        """
        This method used for import all storeview from magento.
        """
        storeview_obj = self.env['magento.storeview']
        api_url = "/V1/store/storeConfigs"
        response = req(self, api_url, method='GET')
        url = "/V1/store/storeViews"
        stores = req(self, url, method='GET')
        for storeview_data in response:
            magento_storeview_id = storeview_data.get('id')
            if magento_storeview_id != 0:
                storeview = storeview_obj.search([
                    ('magento_storeview__id', '=', magento_storeview_id),
                    ('magento_instance_id', '=', self.id)
                ])
                odoo_website_id = self.update_pricelist_in_website(storeview_data)
                if not storeview:
                    name, language = self.get_store_view_language_and_name(
                        stores, magento_storeview_id, storeview_data)
                    code = storeview_data.get('code')
                    base_media_url = storeview_data.get('base_media_url')
                    storeview_obj.create({
                        'name': name,
                        'code': code,
                        'magento_website_id': odoo_website_id.id,
                        'magento_storeview__id': magento_storeview_id,
                        'magento_instance_id': self.id,
                        'base_media_url': base_media_url,
                        'lang_id': language.id
                    })

    def get_store_view_language_and_name(self, stores, magento_storeview_id, storeview_data):
        """
        Get Store view language and name.
        :param stores: Magento stores received from API
        :param magento_storeview_id: Magento store view id
        :param storeview_data: data received from Magento
        :return: name and res language object
        """
        res_lang_obj = self.env['res.lang']
        name = ''
        for store in stores:
            if store['id'] == magento_storeview_id:
                name = store['name']
                break
        lang = storeview_data.get('locale')
        if lang:
            language = res_lang_obj.with_context(active_test=False).search([('code', '=', lang)])
            if language and not language.active:
                language.write({'active': True})
        return name, language

    def update_pricelist_in_website(self, storeview_data):
        """
        If Website is found, then update price list based on store currency.
        :param storeview_data: Store view response received from Magento.
        :return: Magento website object
        """
        website_obj = self.env['magento.website']
        pricelist_obj = self.env['product.pricelist']
        global_channel_obj = self.env['global.channel.ept']
        currency_obj = self.env['res.currency']
        odoo_website_id = website_obj.search([
            ('magento_website_id', '=', storeview_data.get('website_id')),
            ('magento_instance_id', '=', self.id)
        ], limit=1)
        if odoo_website_id:
            currency_id = currency_obj.with_context(active_test=False).search([
                ('name', '=', storeview_data.get('base_currency_code'))], limit=1)
            if currency_id and not currency_id.active:
                currency_id.write({'active': True})
            elif not currency_id:
                currency_id = self.env.user.currency_id
            global_channel_id = global_channel_obj.search([
                ('name', '=', odoo_website_id.name)
            ], limit=1)
            if not global_channel_id:
                global_channel_id = global_channel_obj.create({
                    'name': odoo_website_id.name
                })
            price_list_name = self.name + ' ' + 'PriceList - ' + odoo_website_id.name
            pricelist_id = pricelist_obj.search([
                ('name', '=', price_list_name), ('currency_id', '=', currency_id.id)
            ], limit=1)
            if not pricelist_id:
                pricelist_id = pricelist_obj.create(
                    {'name': price_list_name, 'currency_id': currency_id.id})
            odoo_website_id.write({
                'global_channel_id': global_channel_id,
                'magento_base_currency': currency_id,
                'pricelist_ids': [(6, 0, [pricelist_id.id])],
            })
        return odoo_website_id

    def import_payment_method(self):
        """
        This method used for import payment method.
        """
        payment_method_obj = self.env['magento.payment.method']
        url = '/V1/paymentmethod'
        payment_methods = req(self, url)
        for payment_method in payment_methods:
            payment_method_code = payment_method.get('value')
            new_payment_method = payment_method_obj.search([
                ('payment_method_code', '=', payment_method_code),
                ('magento_instance_id', '=', self.id)
            ])
            if not new_payment_method:
                name = "{} ({})".format(payment_method.get('title'), payment_method.get('value'))
                payment_method_obj.create({
                    'payment_method_code': payment_method.get('value'),
                    'payment_method_name': name,
                    'magento_instance_id': self.id
                })

    def import_delivery_method(self):
        """
        This method used for import delivery method.
        """
        delivery_method_obj = self.env['magento.delivery.carrier']
        url = '/V1/shippingmethod'
        delivery_methods = req(self, url)
        for delivery_method in delivery_methods:
            for method_value in delivery_method.get('value'):
                delivery_method_code = method_value.get('value')
                new_delivery_carrier = delivery_method_obj.search([
                    ('carrier_code', '=', delivery_method_code),
                    ('magento_instance_id', '=', self.id)
                ])
                if not new_delivery_carrier:
                    delivery_method_obj.create({
                        'carrier_code': method_value.get('value'),
                        'carrier_label': method_value.get('label'),
                        'magento_instance_id': self.id,
                        'magento_carrier_title': delivery_method.get('label')
                    })

    def import_magento_inventory_locations(self):
        """
        This method is used to import Magento Multi inventory sources
        :return:
        """
        if self.is_multi_warehouse_in_magento:
            magento_inventory_location_obj = self.env['magento.inventory.locations']
            try:
                api_url = '/V1/inventory/sources'
                response = req(self, api_url)
            except Exception as error:
                raise Warning(_("Error while requesting inventory locations"))
            if response.get('items'):
                for inventory_location in response.get('items'):
                    location_code = inventory_location.get('source_code')
                    magento_location = magento_inventory_location_obj.search([
                        ('code', '=', location_code),
                        ('magento_instance_id', '=', self.id)
                    ])
                    if not magento_location:
                        magento_inventory_location_obj.create({
                            'name': inventory_location.get('name'),
                            'code': inventory_location.get('source_code'),
                            'active': inventory_location.get('enabled'),
                            'magento_instance_id': self.id
                        })
                    else:
                        magento_location.write({'active': inventory_location.get('enabled')})

    def import_tax_class(self):
        """
        This method used for import Tax Classes.
        """
        tax_class_obj = self.env['magento.tax.class.ept']
        url = '/V1/taxClasses/search?searchCriteria[page_size]=50&searchCriteria[currentPage]=1'
        tax_class_req = req(self, url)
        all_tax_class = tax_class_req.get('items')
        for tax_class in all_tax_class:
            tax_class_id = tax_class.get('class_id')
            new_tax_class = tax_class_obj.search([
                ('magento_tax_class_id', '=', tax_class_id),
                ('magento_instance_id', '=', self.id)
            ])
            if not new_tax_class:
                tax_class_obj.create({
                    'magento_tax_class_id': tax_class.get('class_id'),
                    'magento_tax_class_name': tax_class.get('class_name'),
                    'magento_tax_class_type': tax_class.get('class_type'),
                    'magento_instance_id': self.id
                })

    @api.model
    def import_currency(self):
        """
        This method is used to import all currency as pricelist
        :return:
        """
        url = '/V1/directory/currency'
        magento_currency = req(self, url)
        currency_obj = self.env['res.currency']
        magento_base_currency = magento_currency.get('base_currency_code')
        pricelist_obj = self.env['product.pricelist']
        for active_currency in magento_currency.get('exchange_rates'):
            currency_id = currency_obj.search([
                ('name', '=', active_currency.get('currency_to')),
                '|', ('active', '=', False),
                ('active', '=', True)
            ], limit=1)
            if not currency_id.active:
                currency_id.write({'active': True})
            price_list = pricelist_obj.search([('currency_id', '=', currency_id.id)], limit=1)
            if price_list:
                price_list = price_list[0]
            elif not price_list or price_list.currency_id != currency_id:
                price_list = pricelist_obj.create({
                    'name': self.name + " Pricelist - " + active_currency.get('currency_to'),
                    'currency_id': currency_id.id,
                    'discount_policy': 'with_discount',
                    'company_id': self.company_id.id,
                })
            if magento_base_currency == active_currency.get('currency_to') and not self.pricelist_id:
                self.write({'pricelist_id': price_list.id})
            # for mage_website_id in mage_website_ids:
            #     mage_website_id.write({'pricelist_ids': [(4, price_list.id)]})
        return magento_base_currency

    @api.model
    def _scheduler_import_sale_orders(self, args=None):
        """
        This method is used to import sale order from Magento via cron job.
        :param args: arguments to import sale orders
        :return:
        """
        if args is None:
            args = {}
        magento_order_data_queue_obj = self.env['magento.order.data.queue.ept']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            last_order_import_date = instance.last_order_import_date
            if not last_order_import_date:
                last_order_import_date = None
            from_date = last_order_import_date
            to_date = datetime.now()
            magento_order_data_queue_obj.magento_create_order_data_queues(
                instance,
                from_date,
                to_date
            )
            instance.last_order_import_date = datetime.now()

    @api.model
    def _scheduler_import_product(self, args=None):
        """
        This method is used to import product from Magento via cron job.
        :param args: arguments to import products
        :return:
        """
        if args is None:
            args = {}
        magento_import_product_queue_obj = self.env['sync.import.magento.product.queue']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        is_update = args.get('update_existing_product', False)
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            last_product_import_date = instance.last_product_import_date
            if not last_product_import_date:
                last_product_import_date = None
            from_date = last_product_import_date
            to_date = datetime.now()
            magento_import_product_queue_obj.create_sync_import_magento_product_queues(
                instance, from_date, to_date, is_update)

    @api.model
    def _scheduler_update_product_stock_qty(self, args=None):
        """
        This method is used to export product stock quantity to Magento via cron job.
        :param args: arguments to export product stock quantity.
        :return:
        """
        if args is None:
            args = {}
        magento_product_product = self.env['magento.product.product']
        magento_inventory_locations_obj = self.env['magento.inventory.locations']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            if instance.magento_version in ['2.1', '2.2'] or not instance.is_multi_warehouse_in_magento:
                magento_product_product.export_multiple_product_stock_to_magento(instance)
            else:
                inventory_locations = magento_inventory_locations_obj.search([
                    ('magento_instance_id', '=', instance.id)
                ])
                magento_product_product.export_product_stock_to_multiple_locations(
                    instance,
                    inventory_locations
                )

    @api.model
    def _scheduler_update_order_status(self, args={}):
        """
        This method used for when uses cron job it update order status in magento.
        @param  args(instance)
        @author: Haresh Mori
        """
        stock_picking = self.env['stock.picking']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            backend = magento_instance.browse(magento_instance_id)
            stock_picking.export_shipment_to_magento(backend)

    @api.model
    def _scheduler_export_invoice(self, args=None):
        """
        This method is used to export invoices to Magento via cron job.
        :param args: arguments to export invoice
        :return:
        """
        if args is None:
            args = {}
        account_move = self.env['account.move']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            account_move.export_invoice_to_magento(instance)
