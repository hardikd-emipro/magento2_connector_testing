# -*- coding: utf-8 -*-
"""
Describes fields and methods for Magento products
"""
import math
import json
import time
from datetime import datetime, timedelta
from odoo import fields, models, _
from .api_request import req, create_search_criteria
from ..python_library.php import Php
from odoo.exceptions import Warning

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MagentoProductProduct(models.Model):
    """
    Describes fields and methods for Magento products
    """
    _name = 'magento.product.product'
    _description = 'Magento Product'
    _rec_name= 'magento_product_name'

    magento_instance_id = fields.Many2one(
        'magento.instance',
        'Instance',
        help="This field relocates magento instance"
    )
    magento_product_id = fields.Char(string="Magento Product", help="Magento Product Id")
    magento_product_name = fields.Char(
        string="Magento Product Name.",
        help="Magento Product Name.",
        translate=True
    )
    magento_tmpl_id = fields.Many2one(
        'magento.product.template',
        string="Magento Product template",
        help="Magento Product template",
        ondelete="cascade"
    )
    odoo_product_id = fields.Many2one(
        'product.product',
        string='Odoo Product',
        required=True,
        ondelete='restrict',
        copy=False
    )
    website_ids = fields.Many2many(
        'magento.website',
        string='Magento Websites',
        readonly=False,
        domain="[('magento_instance_id','=',magento_instance_id)]",
        help='Magento Websites'
    )
    created_at = fields.Date(
        string='Product Created At',
        help="Date when product created into Magento"
    )
    updated_at = fields.Date(
        string='Product Updated At',
        help="Date when product updated into Magento"
    )
    product_type = fields.Selection([
        ('simple', 'Simple Product'),
        ('configurable', 'Configurable Product'),
        ('virtual', 'Virtual Product'),
        ('downloadable', 'Downloadable Product'),
        ('group', 'Group Product'),
        ('bundle', 'Bundle Product'),
    ], string='Magento Product Type', help='Magento Product Type', default='simple')
    no_stock_sync = fields.Boolean(
        string='No Stock Synchronization',
        help="Check this to exclude the product "
             "from stock synchronizations.",
    )
    export_stock_type = fields.Selection([
        ('fixed', 'Export Fixed Qty'),
        ('actual', 'Export Actual Stock')
    ], string="Export Product Stock Type", default='actual')
    export_fix_value = fields.Float(
        string="Fixed Stock Quantity",
        help="Fixed Stock Quantity"
    )
    magento_sku = fields.Char(string="Magento Product SKU", help="Magento Product SKU")
    description = fields.Text(string="Product Description", help="Description", translate=True)
    short_description = fields.Text(
        string='Product Short Description',
        help='Short Description',
        translate=True
    )
    magento_product_image_ids = fields.One2many(
        'magento.product.image',
        'magento_product_id',
        string="Magento Product Images",
        help="Magento Product Images"
    )
    sync_product_with_magento = fields.Boolean(
        string='Sync Product with Magento',
        help="If Checked means, Product synced With Magento Product"
    )
    active_product = fields.Boolean('Odoo Product Active', related="odoo_product_id.active")
    active = fields.Boolean("Active", default=True)
    image_1920 = fields.Image(related="odoo_product_id.image_1920")
    product_template_attribute_value_ids = fields.Many2many(
        related='odoo_product_id.product_template_attribute_value_ids')
    qty_available = fields.Float(related='odoo_product_id.qty_available')
    lst_price = fields.Float(related='odoo_product_id.lst_price')
    standard_price = fields.Float(related='odoo_product_id.standard_price')
    currency_id = fields.Many2one(related='odoo_product_id.currency_id')
    valuation = fields.Selection(related='odoo_product_id.product_tmpl_id.valuation')
    cost_method = fields.Selection(related='odoo_product_id.product_tmpl_id.cost_method')
    company_id = fields.Many2one(related='odoo_product_id.company_id')
    uom_id = fields.Many2one(related='odoo_product_id.uom_id')
    uom_po_id = fields.Many2one(related='odoo_product_id.uom_po_id')
    total_magento_variants = fields.Integer(related='magento_tmpl_id.total_magento_variants')

    _sql_constraints = [('_magento_product_unique_constraint',
                         'unique(magento_sku,magento_instance_id,magento_product_id)',
                         "Magento Product must be unique")]

    def unlink(self):
        unlink_magento_products = self.env['magento.product.product']
        unlink_magento_templates = self.env['magento.product.template']
        for magento_product in self:
            # Check if the product is last product of this template...
            if not unlink_magento_templates or (unlink_magento_templates and unlink_magento_templates != magento_product.magento_tmpl_id):
                unlink_magento_templates |= magento_product.magento_tmpl_id
            unlink_magento_products |= magento_product
        res = super(MagentoProductProduct, unlink_magento_products).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        if not unlink_magento_templates.magento_product_ids:
            unlink_magento_templates.unlink()
        self.clear_caches()
        return res

    def toggle_active(self):
        """ Archiving related magento.product.template if there is not any more active magento.product.product
        (and vice versa, unarchiving the related magento product template if there is now an active magento.product.product) """
        result = super().toggle_active()
        # We deactivate product templates which are active with no active variants.
        tmpl_to_deactivate = self.filtered(lambda product: (product.magento_tmpl_id.active
                                                            and not product.magento_tmpl_id.magento_product_ids)).mapped('magento_tmpl_id')
        # We activate product templates which are inactive with active variants.
        tmpl_to_activate = self.filtered(lambda product: (not product.magento_tmpl_id.active
                                                          and product.magento_tmpl_id.magento_product_ids)).mapped('magento_tmpl_id')
        (tmpl_to_deactivate + tmpl_to_activate).toggle_active()
        return result

    def view_odoo_product(self):
        """
        This method id used to view odoo product.
        :return: Action
        """
        if self.odoo_product_id:
            return {
                'name': 'Odoo Product',
                'type': 'ir.actions.act_window',
                'res_model': 'product.product',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', '=', self.odoo_product_id.id)],
            }

    def create_magento_product_in_odoo(self, magento_instance, items, magento_per_sku, product_count):
        """
        Create magento product if it is not available in Odoo
        :param magento_instance: Instance of Magento
        :param items: Product items received from Magento
        :param magento_per_sku: Dictionary product sku
        :param product_count: Incremental count of Product
        :return: Dictionary of magento_per_sku and product_count
        """
        common_log_book_obj = self.env['common.log.book.ept']
        common_log_lines_obj = self.env['common.log.lines.ept']
        magento_product_template_obj = self.env['magento.product.template']
        model_id = common_log_lines_obj.get_model_id('magento.product.product')
        job = common_log_book_obj.create({
            'type': 'import',
            'module': 'magento_ept',
            'model_id': model_id,
            'res_id': self.id,
            'magento_instance_id': magento_instance.id
        })
        for item in items:
            error = False
            product_response = json.loads(item.product_data)
            magento_sku = product_response.get('sku')
            if not magento_per_sku or (
                    magento_per_sku and (magento_instance.id not in magento_per_sku.keys() or (
                        magento_instance.id in magento_per_sku.keys() and
                        magento_sku not in magento_per_sku[magento_instance.id].keys()))):
                if product_response.get('type_id') == 'simple':
                    # Simple Product Process
                    job, error = self.create_or_update_magento_simple_product(
                        product_response, magento_instance, job,
                        error, magento_per_sku, item.id,
                        do_not_update=item.do_not_update_existing_product
                    )
                elif product_response.get('type_id') == 'configurable':
                    # Configurable Product Process
                    job, error = magento_product_template_obj.create_or_update_configurable_product(
                        product_response, magento_instance, job, error, magento_per_sku, item.id)
                else:
                    job.write({
                        'log_lines': [(0, 0, {
                            'message': 'Product Type %s Is Not Supported' % product_response.get('type_id'),
                            'order_ref': product_response.get('id'),
                            'import_product_queue_line_id': item.id
                        })]
                    })
                    error = True
            state = 'failed' if error else 'done'
            item.write({'state': state, 'processed_at': datetime.now()})
            product_count += 1
            if product_count > 10:
                self._cr.commit()
                product_count = 1
        if not job.log_lines:
            job.sudo().unlink()
        return magento_per_sku, product_count

    def create_or_update_magento_simple_product(
            self, item, instance, job, error, magento_per_sku,
            order_data_queue_line_id, order_ref=False, magento_prod_tmpl=False, do_not_update=False,
            conf_product_item=False
    ):
        """
        Create or Update Magento And Odoo Product
        :param item: Item received from Magento
        :param instance: Instance of Magento
        :param job: Common log book object
        :param error: If any error, returns True
        :param magento_per_sku: Dictionary of Magento Products
        :return:
        """
        magento_sku = item.get('sku')
        magento_product = self.search([
            ('magento_sku', '=', magento_sku), ('magento_instance_id', '=', instance.id)])
        queue_line = 'import_product_queue_line_id' if not order_ref else 'magento_order_data_queue_line_id'
        order_ref = item.get('id') if not order_ref else order_ref
        website_ids = item.get('extension_attributes').get('website_ids')
        magento_websites = instance.website_ids.filtered(lambda x: x.magento_website_id in str(website_ids))
        self.manage_price_scope(instance, magento_product, item, do_not_update)
        if magento_product and not magento_product.odoo_product_id:
            error = self.map_odoo_product_with_magento_product(
                instance, magento_product, item, job, order_ref, queue_line, order_data_queue_line_id, error
            )
        elif not magento_product:
            odoo_product, error = self.create_odoo_product(
                magento_sku, item, instance, job,
                order_ref, queue_line, order_data_queue_line_id, error
            )
            if odoo_product:
                if not magento_prod_tmpl:
                    magento_prod_tmpl, error = self.create_magento_product_template(
                        odoo_product, instance, item, magento_websites,
                        job, order_ref, queue_line, order_data_queue_line_id, error
                    )
                magento_product, error = self.create_magento_product_product(
                    odoo_product, instance, magento_websites, item, magento_prod_tmpl.id,
                    job, order_ref, queue_line, order_data_queue_line_id, error
                )
        if magento_product:
            self.update_magento_product_and_template(
                item, magento_websites, instance, magento_product, magento_prod_tmpl, conf_product_item)

        if magento_per_sku and instance.id in magento_per_sku.keys():
            magento_per_sku[instance.id][magento_sku] = magento_sku
        else:
            magento_per_sku.update({instance.id: {magento_sku: magento_sku}})
        return job, error

    def map_odoo_product_with_magento_product(
            self, instance, magento_product, item, log_book_id, order_ref, queue_line, order_data_queue_line_id, error
    ):
        """
        Map Odoo Product with existing Magneto Product in Layer
        :param instance: Magento Instance Object
        :param magento_product: Magento product product object
        :param item: Response received from Magento
        :param log_book_id: Common log book object
        :param order_ref: Order reference
        :param queue_line: product or order queue line
        :param order_data_queue_line_id: data queue line object
        :param error: True if error else False
        :return: Log book id, error
        """
        magento_sku = item.get('sku')
        odo_product = magento_product.odoo_product_id.filtered(lambda x: x.default_code == magento_sku)
        if not odo_product:
            odoo_product, error = self.create_odoo_product(
                magento_sku, item, instance, log_book_id,
                order_ref, queue_line, order_data_queue_line_id, error
            )
            if odoo_product:
                magento_product.write({'odoo_product_id': [(0, 0, [odoo_product])]})
        return error

    def create_odoo_product(
            self, magento_sku, prod, instance, log_book_id,
            order_ref, queue_line, order_data_queue_line_id, error
    ):
        """
        Checks and create product in Odoo.
        :param magento_sku: Magento Product SKU
        :param prod: Product items received from Magento
        :param instance: Magento Instance Object
        :param log_book_id: Common log book object
        :param order_ref: order reference
        :param queue_line: product or order queue line
        :param order_data_queue_line_id: queue line object
        :param error: True if error else False
        :return: Product Product Object
        """
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        auto_create_product = instance.auto_create_product
        product_product_obj = self.env['product.product']
        magento_product_template_obj = self.env['magento.product.template']
        odoo_product = product_product_obj.search([('default_code', '=', magento_sku)], limit=1)
        if not odoo_product and auto_create_product:
            magento_websites, description, short_description = magento_product_template_obj.get_magento_websites_and_descriptions(
                instance.id, prod)
            vals = {
                'name': prod.get('name'),
                'default_code': magento_sku,
                'type': 'product',
                'purchase_ok': True,
                'sale_ok': True,
                'invoice_policy': 'order'
            }
            if ir_config_parameter_obj.sudo().get_param("odoo_magento2_ept.set_magento_sales_description"):
                vals.update({
                    'description': short_description,
                    'description_sale': description,
                })
            odoo_product = product_product_obj.create(vals)
        elif not odoo_product and not auto_create_product:
            # Product not found in odoo layer
            # Auto create setting is off for this instance
            message = 'Odoo Product Not found for SKU : %s' \
                      '\nAnd your "Automatically Create Odoo Product If Not Found" ' \
                      'setting is %s' \
                      % (magento_sku, auto_create_product)
            log_book_id.add_log_line(message, order_ref, order_data_queue_line_id, queue_line, magento_sku)
            error = True
        return odoo_product, error

    def create_magento_product_template(self, odoo_product, instance_id, item, magento_websites,
                                        log_book_id, order_ref, queue_line, order_data_queue_line_id, error):
        """
        Create Magento Product Template if not found
        :param odoo_product: Product product object
        :param instance_id: Magento Instance OBJ
        :param item: Item received from Magento
        :param magento_websites: Magento Website Object
        :return: Magento Product Template Object
        """
        magento_prod_tmpl_obj = self.env['magento.product.template']
        magento_prod_tmpl = magento_prod_tmpl_obj.search([
            ('odoo_product_template_id', '=', odoo_product.product_tmpl_id.id),
            ('magento_instance_id', '=', instance_id.id)
        ])
        if not magento_prod_tmpl:
            value = self.prepare_magento_product_vals(item, magento_websites, instance_id.id)
            value.update({
                'magento_product_template_id': item.get('id'),
                'odoo_product_template_id': odoo_product.product_tmpl_id.id,
                'sync_product_with_magento': True
            })
            magento_attribute_set = self.env['magento.attribute.set.ept'].search(
                [('instance_id', '=', instance_id.id), ('attribute_set_id', '=', item.get('attribute_set_id'))])
            if magento_attribute_set:
                value.update({'attribute_set_id': magento_attribute_set.id})
            magento_tax_class = ''
            for attribute_code in item.get('custom_attributes'):
                if attribute_code.get('attribute_code') == 'tax_class_id':
                    magento_tax = self.env['magento.tax.class.ept'].search([
                        ('magento_instance_id', '=', instance_id.id),
                        ('magento_tax_class_id', '=', attribute_code.get('value'))])
                    magento_tax_class = magento_tax.id
            if magento_tax_class:
                value.update({'magento_tax_class': magento_tax_class})
            magento_categories_dict = []
            if 'category_links' in item.get('extension_attributes'):
                for attribute_code in item.get('extension_attributes').get('category_links'):
                    magento_categories_dict.append(attribute_code.get('category_id'))
                if magento_categories_dict:
                    magento_categories = self.env['magento.product.category.ept'].search([
                        ('instance_id', '=', instance_id.id),
                        ('category_id', 'in', magento_categories_dict)])
                    value.update({'category_ids': [(6, 0, magento_categories.ids)]})
            magento_prod_tmpl = magento_prod_tmpl_obj.create(value)
            if instance_id.allow_import_image_of_products and item.get('type_id') == "configurable":
                magento_media_url = False
                magento_stores = magento_websites.store_view_ids
                if magento_stores:
                    magento_media_url = magento_stores[0].base_media_url
                if magento_media_url:
                    full_img_url, error = magento_prod_tmpl_obj.create_or_update_product_images(
                        instance_id, False, magento_prod_tmpl,
                        magento_media_url, item.get('media_gallery_entries'),
                        log_book_id, order_ref, queue_line, order_data_queue_line_id, error
                    )
            self._cr.commit()
        return magento_prod_tmpl, error

    def prepare_magento_product_vals(self, item, magento_websites, instance_id):
        """
        Prepare vals for Magento product and template
        :param item: Item received from Magento
        :param magento_websites: Magento Website Object
        :param instance_id: Magento Instance Id
        :return: Return dictionary of values
        """
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        description = short_description = ''
        for attribute_code in item.get('custom_attributes'):
            if attribute_code.get('attribute_code') == 'description':
                description = attribute_code.get('value')
            if attribute_code.get('attribute_code') == 'short_description':
                short_description = attribute_code.get('value')
        magento_product_vals = {
            'magento_product_name': item.get('name'),
            'magento_instance_id': instance_id,
            'website_ids': [(6, 0, magento_websites.ids)],
            'magento_sku': item.get('sku'),
            'product_type': item.get('type_id'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
        }
        if ir_config_parameter_obj.sudo().get_param("odoo_magento2_ept.set_magento_sales_description"):
            magento_product_vals.update({
                'description': description,
                'short_description': short_description,
            })
        return magento_product_vals

    def create_magento_product_product(self, odoo_product, instance, magento_websites, item, magento_prod_tmpl_id,
                                       log_book_id, order_ref, queue_line, order_data_queue_line_id, error):
        """
        Create Magento Product if not found
        :param odoo_product: Odoo Product Object
        :param instance: Magento Instance Object
        :param magento_websites: Magento Website Object
        :param item: Item received from Magento
        :param magento_prod_tmpl_id:  Magento Product Template Id
        :return:
        """
        magento_prod_tmpl_obj = self.env['magento.product.template']
        magento_product = self.search([
            ('odoo_product_id', '=', odoo_product.id),
            ('magento_instance_id', '=', instance.id)])
        if not magento_product and odoo_product.default_code == item.get('sku'):
            values = self.prepare_magento_product_vals(item, magento_websites, instance.id)
            values.update({
                'magento_product_id': item.get('id'),
                'magento_tmpl_id': magento_prod_tmpl_id,
                'odoo_product_id': odoo_product.id,
                'sync_product_with_magento': True
            })
            magento_product = self.create(values)
            price = item.get('price') or 0.0
            self.create_pricelist_item(instance, price, magento_product, item)
            if instance.allow_import_image_of_products:
                magento_media_url = False
                magento_stores = magento_websites.store_view_ids
                if magento_stores:
                    magento_media_url = magento_stores[0].base_media_url
                if magento_media_url:
                    full_img_url, error = magento_prod_tmpl_obj.create_or_update_product_images(
                        instance, magento_product, False,
                        magento_media_url, item.get('media_gallery_entries'),
                        log_book_id, order_ref, queue_line, order_data_queue_line_id, error
                    )
            self._cr.commit()
        return magento_product, error

    def update_magento_product_and_template(
            self, item, magento_websites, instance, magento_product, magento_prod_tmpl, conf_product_item):
        """
        Update Magento Product and product template details.
        :param item: Item received from Magento
        :param magento_websites: Magento website object
        :param instance: Magento instance object
        :param magento_product: Magento product object
        :param magento_prod_tmpl: Magento product template object or False
        :param conf_product_item: Child product items received from Magento
        :return: Magento product object
        """
        self.update_magento_product(item, magento_websites, instance, magento_product)
        # below code for set magento sku and magento product id while import
        # the product and product was already mapped before perform the import operation
        template_vals = {}
        if not magento_prod_tmpl and (
                (not magento_product.magento_tmpl_id.magento_product_template_id or
                 not magento_product.magento_tmpl_id.magento_sku)
                or
                (magento_product.magento_tmpl_id and
                 magento_product.odoo_product_id.product_tmpl_id)
        ):
            # case 1 (configurable product): map product first.
            # So magento product id and created and updated date not set in the template
            # now while import that same configurable product then update that template and
            # set magento product ID and other value
            # Case 2 : During the time of the map product if not set the magento SKU
            # then set the magento sku as well
            # Case 3 : While import product first time and then change the product data from the magento
            # then update that data in magento layer product template as well
            itm = conf_product_item if conf_product_item else item
            if itm.get('sku') == magento_product.magento_tmpl_id.magento_sku:
                # While configurable product's simple product update
                # at that time template name and type was changed,
                # So this condition added
                template_vals = magento_product.magento_tmpl_id.prepare_magento_product_template_vals(
                    itm, instance, magento_product.odoo_product_id.product_tmpl_id)
                template_vals.pop('magento_product_name')  # not change the product name,
                # because it's change the odoo product/template name as well
        if template_vals or not magento_product.magento_tmpl_id.magento_sku:
            # Add "or" condition for below case
            # case : first map the product and then import that specific product,
            # So set the magento template id and sku
            if conf_product_item:
                conf_product_item_id = conf_product_item.get('id')
                conf_product_item_sku = conf_product_item.get('sku')
                magento_product_type = 'configurable'
            else:
                conf_product_item_id = item.get('id')
                conf_product_item_sku = item.get('sku')
                magento_product_type = 'simple'
            template_vals.update({
                'magento_product_template_id': conf_product_item_id,
                'magento_sku': conf_product_item_sku,
                'product_type': magento_product_type,
                'sync_product_with_magento': True
            })
            magento_product.magento_tmpl_id.write(template_vals)
        return True

    def update_magento_product(self, item, magento_websites, instance, magento_product):
        """
        magento product found, then prepare the new magento product vals and write it
        :param item: product item API response
        :param magento_websites: website data
        :param instance:  magento instance
        :param magento_product: magento product object
        :return:
        """
        values = self.prepare_magento_product_vals(item, magento_websites, instance.id)
        values.update({
            'magento_product_id': item.get('id'),
            'magento_tmpl_id': magento_product.magento_tmpl_id.id,
            'odoo_product_id': magento_product.odoo_product_id.id,
            'sync_product_with_magento': True
        })
        # Below code is for all the configurable's simple product is only simple product in odoo
        # not map all this odoo simple with configurable's simple product
        # and import configurable product, so set all the simple product's id and sync as true in magento.product.template
        magento_product_tmpl = self.env['magento.product.template'].search(
            [('magento_product_template_id', '=', False), ('sync_product_with_magento', '=', False),
             ('magento_sku', '=', magento_product.magento_sku)])
        if magento_product_tmpl:
            magento_product_tmpl.write({
                'magento_product_template_id': item.get('id'),
                'sync_product_with_magento': True
            })
        magento_product.write(values)

    def get_magento_product_by_id(self, magento_instance, magento_id, product_ids=None):
        """
        This method is used to call API for getting product data from magento.
        :param magento_instance: Instance of Magento
        :param magento_id: Magento Product Id
        :param product_ids: Dictionary of product get from magento
        :return:
        """
        if product_ids is None:
            product_ids = []
        magento_product_product_obj = self.env['magento.product.product']
        if product_ids:
            #Get Magento Products from product id instead of SKU
            #Reason: to resolve API issue if sku has / in it for ex[sku = 'XX/XX/XX']
            final_prod_response = self.get_magento_product_from_entity_id(magento_instance, product_ids)
            return final_prod_response
        magento_product = magento_product_product_obj.search([
            ('magento_product_id', '=', magento_id),
            ('magento_instance_id', '=', magento_instance.id)
        ])
        sku = magento_product and magento_product.magento_sku
        if not sku:
            filters = {'entity_id': magento_id}
            filters = create_search_criteria(filters)
            query_str = Php.http_build_query(filters)
            api_url = "/V1/products?%s" % (query_str)
            try:
                response = req(magento_instance, api_url)
            except:
                raise Warning("Error while requesting product")
            return response.get('items')[0].get('sku') if response.get('items') else False
        return sku

    def get_magento_product_from_entity_id(self, instance, product_ids):
        """
        Get products data from Magento from entity id.
        :param instance:magento.instance()
        :param product_ids:list
        :return:list
        """
        result_list = []
        for product_id in product_ids:
            filter ={'entity_id':product_id}
            search_criteria = create_search_criteria(filter)
            query_string = Php.http_build_query(search_criteria)
            try:
                api_url = '/V1/products?%s' % query_string
                response = req(instance, api_url)
                if response.get('items'):
                    result_list.append(response.get('items')[0])
            except Exception as error:
                raise Warning(_("Error while requesting products {}".format(error)))
        return result_list

    def get_magento_product_by_sku(self, magento_instance, prod_response, queue_line, error,
                                   log_book_id, order_data_queue_line_id):
        """
        This method is used to call API for getting product data from magento.
        :param magento_instance: Instance of Magento
        :param prod_response: Dictionary of product sku get from magento
        :param queue_line: Sync import magento product queue line object
        :param error: True if any error else False
        :param log_book_id: common log book object
        :param order_data_queue_line_id: Sync import magento product queue line id
        :return:
        """
        final_prod_res = {}
        result_list = []
        for prod_res in prod_response:
            try:
                sku = Php.quote_sku(prod_res.get('sku'))
                api_url = '/V1/products/%s' % format(sku)
                response = req(magento_instance, api_url)
                result_list.append(response)
            except Exception:
                if log_book_id:
                    # Before process queue, delete some configurable's simple product.
                    # So mark that queue as Failed state and add log line
                    message = 'Magento Product not found with SKU %s' % prod_res.get('sku')
                    log_book_id.add_log_line(message, False,
                                             order_data_queue_line_id,
                                             queue_line,
                                             prod_res.get('sku'))
                    error = True
        final_prod_res.update({'items': result_list})
        return final_prod_res, error

    def create_or_update_product_in_magento(self, order_responses, magento_instance, magento_per_sku,
                                            order_ref, order_data_queue_line_id):
        """
        Create or update product when import orders from Magento.
        :param order_responses: Order Response received from Magento
        :param magento_instance: Instance of Magento
        :param magento_per_sku: Dictionary of Magento Product
        :param order_ref: Order reference
        :param order_data_queue_line_id: Order data queue line id
        :return: common log book object and skip order
        """
        common_log_book_obj = self.env['common.log.book.ept']
        common_log_lines_obj = self.env['common.log.lines.ept']
        model_id = common_log_lines_obj.get_model_id('magento.product.product')
        skip_order = False
        job = common_log_book_obj.create({
            'type': 'import',
            'module': 'magento_ept',
            'model_id': model_id,
            'res_id': self.id,
            'magento_instance_id': magento_instance.id
        })
        for order_response in order_responses:
            # Check the ordered product is already exist in the magento product product layer or not.
            # If product is already exist then no need to again send the API call.
            # Used existing product.
            magento_product_obj = self.env['magento.product.product'].search([
                ('magento_instance_id', '=', magento_instance.id), '|',
                ('magento_product_id', '=', order_response.get('product_id')),
                ('magento_sku', '=', order_response.get('sku'))], limit=1)
            product_obj = self.env['product.product'].search([('default_code', '=', order_response.get('sku'))])
            if order_response.get('product_type') in ['grouped', 'bundle'] and not product_obj:
                skip_order = True
                message = _(
                    "Order '{}' has been skipped because the product type '{}' SKU '{}' is not found in Odoo. \n"
                    "Please create the product in Odoo with the same SKU to import the order. \n"
                    "Note: \n"
                    "- In the case where the Magento product type is a group, please create a Storable or "
                    "Service type product with the same SKU for every child product of the Magento group. \n"
                    "- Create a Service type product in Odoo if the Magento group's child product is virtual or "
                    "downloadable, and if the child product is simple in Magento, create a storable \n"
                    "type product in Odoo with the same SKU. \n").format(
                    order_ref, order_response.get('product_type'),
                    order_response.get('sku'))
                job.write({
                    'log_lines': [(0, 0, {
                        'message': message,
                        'order_ref': order_ref,
                        'magento_order_data_queue_line_id': order_data_queue_line_id
                    })]
                })
                break
            elif not magento_product_obj and order_response.get('product_type') not in ['grouped', 'bundle']:
                try:
                    # every time send the product API call by using product id.
                    # To stop the product API call by using SKU because at that time
                    # wrong product id set in the magento product template and also
                    # create only single simple product which was ordered (Configurable product)
                    # Using this code if only single simple product ordered then also if main
                    # configurable product not found then create that main configurable product with all the variants.

                    filter = {'entity_id': order_response.get('product_id')}
                    search_criteria = create_search_criteria(filter)
                    query_string = Php.http_build_query(search_criteria)
                    api_url = '/V1/products?%s' % query_string
                    response = req(magento_instance, api_url).get('items')[0]
                except:
                    # Add below code for while order processing and product
                    # not found for the particular queue line then add log line and skip that queue line.
                    message = _("Error While Requesting Product SKU %s" % order_response.get('sku'))
                    job.write({
                        'log_lines': [(0, 0, {
                            'message': message,
                            'order_ref': order_ref,
                            'magento_order_data_queue_line_id': order_data_queue_line_id
                        })]
                    })
                    continue
                magento_sku = response.get('sku')
                if product_obj and order_response.get('product_type') in ['virtual', 'downloadable']:
                    job, skip_order = self.create_or_update_magento_simple_product(
                        response, magento_instance, job, skip_order, magento_per_sku,
                        order_data_queue_line_id, order_ref)
                else:
                    job, skip_order = self.create_or_update_magento_product(
                        order_response, response, magento_sku, magento_instance, job,
                        skip_order, magento_per_sku, order_data_queue_line_id, order_ref)
        if not job.log_lines:
            job.sudo().unlink()
        else:
            skip_order = True
        return skip_order, job

    def create_or_update_magento_product(
            self, order_response, response, magento_sku, magento_instance, job,
            skip_order, magento_per_sku, order_data_queue_line_id, order_ref):
        magento_product_template_obj = self.env['magento.product.template']
        if not magento_per_sku or (
                magento_per_sku and (magento_instance.id not in magento_per_sku.keys() or (
                magento_instance.id in magento_per_sku.keys() and
                magento_sku not in magento_per_sku[magento_instance.id].keys()))):

            # Check product is simple type then sku of the order response and magento sku both are same.
            # If ordered product is simple product and also have custom option. Then Ordered product sku and magento sku not same.
            # So in that case need to check ordered product id and response product ID.
            if order_response.get('product_type') == 'simple' and (
                    order_response.get('product_id') == response.get('id')
                    or order_response.get('sku') == magento_sku):
                # Simple Product Process
                job, skip_order = self.create_or_update_magento_simple_product(
                    response, magento_instance, job, skip_order, magento_per_sku,
                    order_data_queue_line_id, order_ref)
            # Check product type is configurable then in the ordered response we get simple product SKU and
            # in the magento SKU we get main Configurable product sku. So Both are not same.
            elif order_response.get('product_type') == 'configurable' and order_response.get('sku') != magento_sku:
                # Configurable Product Process
                job, skip_order = magento_product_template_obj.create_or_update_configurable_product(
                    response, magento_instance, job, skip_order,
                    magento_per_sku, order_data_queue_line_id, order_ref)
            else:
                message = _("Order {} was skipped because when importing order the product {} "
                            "could not find in the odoo. \n "
                            "Please create the product in Odoo with the same SKU to import the order.".format(
                    order_ref, order_response.get('sku')))
                job.write({
                    'log_lines': [(0, 0, {
                        'message': message,
                        'order_ref': order_ref,
                        'magento_order_data_queue_line_id': order_data_queue_line_id
                    })]
                })
        return job, skip_order

    def manage_price_scope(self, instance, magento_product, item, do_not_update):
        """
        :param instance: Magento Instance
        :param magento_product: magento Product
        :param item: Item received from Magento
        :param do_not_update: If True, it will update existing magento product.
        :return:
        """
        # Case : Price Scope = Global
        # ===========================================
        # add this for update price in the price-list
        # if the product and it's price is exist in configured price-list then update
        # else create new line in price-list with that simple product and price
        # Case : Price Scope = Website
        # ===========================================
        # If price scope is "website" then add product price in the configured -
        # price-list. [Path : Magento Instance > Magento Websites > price-list]
        # if bool object for the price update is checked then only price -
        # update if the product was exist in that price-list
        # If the bool obj of the update price not checked any product not exist
        # in the price-list then also the price will be added to the configured price-list
        # Add/Update Price Based on the magento Default Price
        price = item.get('price') or 0.0
        if magento_product and not do_not_update:
            self.create_pricelist_item(instance, price, magento_product, item)

    def create_pricelist_item(self, magento_instance, price, product, item):
        """
        Added product into price list.
        :param magento_instance: Instance of Magento
        :param price: Product Price
        :param product: Magento Product object
        :return: product pricelist item object
        """
        pricelist_item_obj = self.env['product.pricelist.item']
        if magento_instance.catalog_price_scope == 'global':
            pricelist_id = magento_instance.pricelist_id.id
            pricelist_item = pricelist_item_obj.search([
                ('pricelist_id', '=', pricelist_id),
                ('product_id', '=', product.odoo_product_id.id)
            ])
            self.create_or_update_price(pricelist_id, product, price, pricelist_item)
        elif item.get('extension_attributes').get('website_wise_product_price_data'):
            for website_product_price in item.get('extension_attributes').get(
                    'website_wise_product_price_data'):
                website_product_price = json.loads(website_product_price)
                magento_website = self.env['magento.website']. \
                    search([('magento_website_id', '=', website_product_price.get('website_id'))],
                           limit=1)
                if magento_website:
                    pricelist_ids = magento_website.pricelist_ids
                    price = website_product_price.get('product_price')
                    website_pricelist = self.get_website_price_list(website_product_price,
                                                                    pricelist_ids)
                    if website_pricelist:
                        pricelist_items = pricelist_item_obj. \
                            search([('pricelist_id', '=', website_pricelist.id),
                                    ('product_id', '=', product.odoo_product_id.id)])
                        self.create_or_update_price(website_pricelist.id,
                                                    product,
                                                    price, pricelist_items)

    def get_website_price_list(self, website_product_price, pricelist_ids):
        """
        Get price list of products magento website vise.
        :param website_product_price: website wise product price
        :param pricelist_ids: product pricelist ids
        :return:
        """
        default_store_currency = website_product_price.get('default_store_currency')
        currency_obj = self.env['res.currency']
        currency_id = currency_obj.with_context(active_test=False). \
            search([('name', '=', default_store_currency)], limit=1)
        return pricelist_ids.filtered(lambda x: x.currency_id.id == currency_id.id)

    def create_or_update_price(self, pricelist_id, product, price, pricelist_item):
        pricelist_item_obj = self.env['product.pricelist.item']
        if pricelist_item:
            pricelist_item.write({'fixed_price': price})
        else:
            pricelist_item_obj.create({
                'pricelist_id': pricelist_id,
                'applied_on': '0_product_variant',
                'product_id': product.odoo_product_id.id,
                'product_tmpl_id': product.odoo_product_id.product_tmpl_id.id,
                'compute_price': 'fixed',
                'min_quantity': 1,
                'fixed_price': price
            })

    def create_product_inventory(self, instance, validate_stock):
        """
        This method is used to import product stock from magento,
        when Multi inventory sources is not available.
        It will create a product inventory.
        :param instance: Instance of Magento
        :param validate_stock: True if auto validate inventory adjustments else False
        :return: True
        """
        stock_inventory = self.env['stock.inventory']
        common_log_book_obj = self.env['common.log.book.ept']
        model_id = self.env['common.log.lines.ept'].get_model_id('magento.product.product')
        job = common_log_book_obj.create({
            'name': 'Import Product Stock',
            'type': 'import',
            'module': 'magento_ept',
            'model_id': model_id,
            'res_id': self.id,
            'magento_instance_id': instance.id,
        })
        if instance.is_import_product_stock:
            import_stock_location = instance.import_stock_warehouse
            location = import_stock_location and import_stock_location.lot_stock_id
            if location:
                page_count = 1
                stock_data = self.get_magento_stock_data_ept(instance, page_count)
                total_count = stock_data.get('total_count')
                if total_count == 0:
                    raise Warning("Products has been not found for import stocks.")
                stock_to_import = self.get_list_of_magento_inventory(stock_data.get('items'), job)
                if stock_to_import:
                    stock_inventory.create_stock_inventory(stock_to_import, location, validate_stock)
                    self._cr.commit()
                while (page_count * 200) <= total_count:
                    page_count += 1
                    stock_data = self.get_magento_stock_data_ept(instance, page_count)
                    stock_to_import = self.get_list_of_magento_inventory(stock_data.get('items'), job)
                    if stock_to_import:
                        stock_inventory.create_stock_inventory(stock_to_import, location, validate_stock)
                        self._cr.commit()
            else:
                raise Warning("Please Choose Import product stock for %s location" % import_stock_location.name)
        return True

    def get_list_of_magento_inventory(self, stock_items, job):
        stock_to_import = []
        consumable_products = []
        log_lines = []
        magento_product_product = self.env['magento.product.product']
        product_ids = [item.get('product_id') for item in stock_items]
        products = magento_product_product.search([('magento_product_id', 'in', product_ids)])
        for item in stock_items:
            product = products.filtered(lambda p: p.magento_product_id == str(item.get('product_id')))
            if product:
                qty = item.get('qty') if item.get('qty') else 0.0
                odoo_product = product.odoo_product_id if product.odoo_product_id else False
                if qty > 0.0 and odoo_product and odoo_product.type != 'product':
                    consumable_products.append(odoo_product.default_code)
                elif qty > 0.0 and odoo_product:
                    stock_dict = {'product_qty': qty, 'product_id': odoo_product}
                    stock_to_import.append(stock_dict)
                else:
                    log_line_vals = {'message': 'Product Quantity in Magento is {} for Magento Product ID {}'.format(
                        qty, item.get('product_id'))} if odoo_product else \
                        {'message': 'Odoo Product not found for Magento Product Id {}'.format(item.get('product_id'))}
                    log_lines.append((0, 0, log_line_vals))
            else:
                log_line_vals = {'message': 'Magento Product with Product ID {} not found.'.format(item.get('product_id'))}
                log_lines.append((0, 0, log_line_vals))
        if consumable_products:
            log_line_vals = {
                'message': "The following products have not been imported due to "
                           "product type is other than 'Storable.'\n{}".format(str(list(set(consumable_products))))}
            log_lines.append((0, 0, log_line_vals))
        if log_lines:
            job.write({'log_lines':log_lines})
        return stock_to_import

    def get_magento_stock_data_ept(self, instance, page_count):
        """
        Create Query String and call Magento StockItem/lowStock API
        :param instance: magento.instance
        :param scopeId: Stock Scope from Magento
        :param quantity: int|float
        :param page_count: int
        :return: dictionary
        """
        scopeId = instance.magento_import_stock_scope_id
        quantity = instance.magento_import_stock_min_qty
        query_string = "scopeId={}&qty={}&pageSize=200&currentPage={}".format(scopeId, quantity, page_count)
        url = '/V1/stockItems/lowStock/?%s' % query_string
        stock_data = req(instance, url)
        time.sleep(2)
        return stock_data

    def create_product_multi_inventory(self, instance, magento_locations, validate_stock):
        """
        This method is used to import product stock from magento,
        when Multi inventory sources is available.
        It will create a product inventory.
        :param instance: Instance of Magento
        :param magento_locations: Magento products object
        :param validate_stock: True if auto validate inventory adjustments else False
        :return: True
        """
        stock_inventory = self.env['stock.inventory']
        magento_product_obj = self.env['magento.product.product']
        if instance.is_import_product_stock:
            consumable_products = []
            model_id = self.env['common.log.lines.ept'].get_model_id('stock.inventory')
            log_book_id = self.env["common.log.book.ept"].create({
                'type': 'import',
                'module': 'magento_ept',
                'model_id': model_id,
                'magento_instance_id': instance.id
            })
            for magento_location in magento_locations:
                stock_to_import = []
                import_stock_location = magento_location.import_stock_warehouse
                location = import_stock_location and import_stock_location.lot_stock_id
                if location:
                    filters = {'source_code': magento_location.code}
                    search_criteria = create_search_criteria(filters)
                    query_string = Php.http_build_query(search_criteria)
                    try:
                        api_url = '/V1/inventory/source-items?%s' % query_string
                        response = req(instance, api_url)
                    except Exception as error:
                        raise Warning(_("Error while requesting products"))
                    if response.get('items'):
                        for inventory in response.get('items'):
                            magento_prod = magento_product_obj.search([
                                ('magento_sku', '=', inventory.get('sku')),
                                ('magento_instance_id', '=', instance.id)
                            ])
                            if magento_prod:
                                qty = inventory.get('quantity') or False
                                if qty and qty > 0.0:
                                    if magento_prod.odoo_product_id.type != 'product':
                                        consumable_products.append(magento_prod.odoo_product_id.default_code)
                                    else:
                                        stock_dict = {
                                            'product_id': magento_prod.odoo_product_id,
                                            'product_qty': qty,
                                            'location_id': location
                                        }
                                        stock_to_import.append(stock_dict)
                    stock_inventory.create_stock_inventory(stock_to_import, location, validate_stock)
                else:
                    raise Warning(_("Please Choose Import Product Stock Warehouse for %s, "
                                    "from Magento > Configuration > Magento Inventory Locations.") % magento_location.name)
            self.create_import_product_process_log(consumable_products, log_book_id)
        return True

    @staticmethod
    def create_import_product_process_log(consumable_products, log_book_id):
        """
        Generate process log for import product stock with consumable product.
        :param consumable_products: dictionary of consumable products
        :param log_book_id: common log book object
        """
        if consumable_products:
            message = "The following products have not been imported due to " \
                      "product type is other than 'Storable.'\n %s" % str(list(set(consumable_products)))
            log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': message
                })]
            })

    @staticmethod
    def create_export_product_process_log(consumable_products, log_book_id):
        """
        Generate process log for export product stock with consumable product.
        :param consumable_products: dictionary of consumable products
        :param log_book_id: common log book object
        """
        if consumable_products:
            message = "The following products have not been exported due to " \
                      "product type is other than 'Storable.'\n %s" % str(list(set(consumable_products)))
            log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': message
                })]
            })

    def export_multiple_product_stock_to_magento(self, instance):
        """
        This method is used to export multiple product stock from odoo to magento.
        :param instance: Instance of Magento
        :return:
        """
        stock_data = []
        consumable_products = []
        model_id = self.env['common.log.lines.ept'].get_model_id('magento.product.product')
        job = self.env['common.log.book.ept'].create({
            'name': 'Export Product Stock', 'type': 'export', 'module': 'magento_ept',
            'model_id': model_id, 'res_id': self.id, 'magento_instance_id': instance.id})
        export_product_stock = self.get_export_product_stock(instance, instance.warehouse_ids)
        if export_product_stock:
            for product_stock in export_product_stock:
                exp_product = self.search([
                    ('odoo_product_id', '=', product_stock.get('product_id')),
                    ('magento_instance_id', '=', instance.id)], limit=1)
                stock = product_stock.get('stock')
                if exp_product and stock >= 0.0:
                    if exp_product.odoo_product_id.type != 'product':
                        consumable_products.append(exp_product.odoo_product_id.default_code)
                    else:
                        product_stock_dict = {'sku': exp_product.magento_sku, 'qty': stock,
                                              'is_in_stock': 1}
                        stock_data.append(product_stock_dict)
        self.create_export_product_process_log(consumable_products, job)
        if stock_data:
            api_url = "/V1/product/updatestock"
            job = self.exp_prd_stock_in_batches(stock_data, instance, api_url, 'skuData', 'PUT', job)
        if not job.log_lines:
            job.sudo().unlink()

    def export_product_stock_to_multiple_locations(self, instance, magento_locations):
        """
        This method is used to export product stock to magento,
        when Multi inventory sources is available.
        It will create a product inventory.
        :param instance: Instance of Magento
        :param magento_locations: Magento products object
        :return: True
        """
        stock_data = []
        consumable_products = []
        model_id = self.env['common.log.lines.ept'].get_model_id('magento.product.product')
        job = self.env['common.log.book.ept'].create({
            'name': 'Export Product Stock', 'type': 'export', 'module': 'magento_ept',
            'model_id': model_id, 'res_id': self.id, 'magento_instance_id': instance.id})
        for magento_location in magento_locations:
            export_stock_locations = magento_location.mapped('export_stock_warehouse_ids')
            if export_stock_locations and export_stock_locations.ids:
                export_product_stock = self.get_export_product_stock(instance,
                                                                     export_stock_locations)
                if export_product_stock:
                    for product_stock in export_product_stock:
                        stock_data = self.prepare_export_product_stock_dict(
                            product_stock, instance, consumable_products, stock_data,
                            magento_location)
            else:
                raise Warning(
                    _("Please Choose Export product stock location for %s" % magento_location.name))
        self.create_export_product_process_log(consumable_products, job)
        if stock_data:
            api_url = "/V1/inventory/source-items"
            job = self.exp_prd_stock_in_batches(stock_data, instance, api_url, 'sourceItems', 'POST', job)
        if not job.log_lines:
            job.sudo().unlink()
        return True

    def exp_prd_stock_in_batches(self, stock_data, instance, api_url, data_key, method, job):
        """
        Export product stock in a bunch of 100 items.
        :param stock_data: dictionary for stock data
        :param instance: magento instance object
        :param api_url: export stock API url
        :param data_key: API dictionary key
        :param method: API method
        :param job: common log book object
        :return: common log book object
        """
        current_page = 1
        start_range = 0
        total_stock_dict_pages = math.ceil(len(stock_data) / 100)
        end_range = start_range + 99 if total_stock_dict_pages > 1 else len(stock_data) - 1
        for page in range(current_page, total_stock_dict_pages + 1):
            stock_dict = [stock_data[x] if stock_data else [] for x in range(start_range, end_range + 1)]
            if stock_dict:
                data = {data_key: stock_dict}
                job = self.call_export_product_stock_api(instance, api_url, data, job, method)
                start_range = start_range + 100
                end_range = start_range + 99
                if page + 1 == total_stock_dict_pages:
                    end_range = len(stock_data) - 1
        return job

    def prepare_export_product_stock_dict(
            self, product_stock, instance, consumable_products, stock_data, magento_location):
        """
        Prepare Export Product Stock Dictionary
        :param product_stock: Odoo product stock
        :param instance: Magneto instance
        :param consumable_products: dictionary for consumable products
        :param stock_data: dictionary for export product stock
        :param magento_location: magento inventory location object
        :return: dictionary for export product stock
        """
        exp_product = self.search([
            ('odoo_product_id', '=', product_stock.get('product_id')), ('magento_instance_id', '=', instance.id)
        ], limit=1)
        stock = product_stock.get('stock')
        if exp_product and stock >= 0.0:
            if exp_product.odoo_product_id.type != 'product':
                consumable_products.append(exp_product.odoo_product_id.default_code)
            else:
                stock_data.append({'sku': exp_product.magento_sku,
                                   'source_code': magento_location.code,
                                   'quantity': stock, 'status': 1})
        return stock_data

    def get_export_product_stock(self, instance, export_stock_locations):
        """
        Get export product stock dictionary with stock.
        :param instance: Magento instance object
        :param export_stock_locations: Stock location object
        :return: Export product stock dictionary.
        """
        product_product_obj = self.env['product.product']
        instance_export_date = instance.last_update_stock_time
        if not instance_export_date:
            instance_export_date = datetime.today() - timedelta(days=365)
        product_ids = product_product_obj.get_products_based_on_movement_date(
            instance_export_date, instance.company_id
        )
        product_ids = [product_id.get('product_id') for product_id in product_ids]
        export_product_stock = self.get_magento_product_stock_ept(
            instance, product_ids, product_product_obj, export_stock_locations)
        return export_product_stock

    @staticmethod
    def call_export_product_stock_api(instance, api_url, data, job, method_type):
        """
        Call export product stock API for single or multi tracking inventory.
        :param instance: Magento instance object
        :param api_url: API Call URL
        :param data: Dictionary to be passed.
        :param job: Common log book object
        :param method_type: Api Request Method type (PUT/POST)
        :return: common log book object
        """
        try:
            responses = req(instance, api_url, method_type, data)
        except Exception as error:
            raise Warning(_("Error while Export product stock " + str(error)))
        if responses:
            for response in responses:
                if isinstance(response, dict):
                    message = response.get('message')
                else:
                    message = responses.get(response)
                job.write({'log_lines': [(0, 0, {'message': message})]})
        return job

    @staticmethod
    def get_magento_product_stock_ept(instance, product_ids, prod_obj, warehouse):
        """
        This Method relocates check type of stock.
        :param instance: This arguments relocates instance of amazon.
        :param product_ids: This arguments product listing id of odoo.
        :param prod_obj: This argument relocates product object of common connector.
        :param warehouse:This arguments relocates warehouse of amazon.
        :return: This Method return product listing stock.
        """
        product_listing_stock = False
        if product_ids:
            prod_ids = prod_obj.browse(product_ids)
            if instance.magento_stock_field == 'free_qty':
                product_listing_stock = prod_obj.get_qty_on_hand(warehouse, prod_ids)
            elif instance.magento_stock_field == 'virtual_available':
                product_listing_stock = prod_obj.get_forecated_qty(warehouse, prod_ids)
        return product_listing_stock
