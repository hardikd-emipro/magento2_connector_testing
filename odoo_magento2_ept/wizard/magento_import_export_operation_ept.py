#!/usr/bin/python3
"""
Describes product import export process.
"""
import base64
import csv
import xlrd
import io
import os
from csv import DictWriter
from io import StringIO
from datetime import datetime, timedelta
from odoo.tools.misc import xlsxwriter
from odoo import fields, models, api, _
from odoo.exceptions import Warning, ValidationError

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MagentoImportExportEpt(models.TransientModel):
    """
    Describes Magento Process for import/ export operations
    """
    _name = 'magento.import.export.ept'
    _description = 'Magento Import Export Ept'

    magento_instance_ids = fields.Many2many(
        'magento.instance',
        string="Instances",
        help="This field relocates Magento Instance"
    )
    operations = fields.Selection([
        ('map_products', 'Map Products'),
        ('import_products', 'Import Products'),
        ('export_product_stock', 'Export Stock'),
        ('export_shipment_information', 'Export Shipment Information'),
        ('import_sale_order', 'Import Sale Order'),
        ('import_product_stock', 'Import Stock'),
        ('import_customer', 'Import Customer'),
        ('import_product_categories', 'Import Categories'),
        ('import_product_attributes', 'Import Attributes'),
        ('import_specific_product', 'Import Specific Product(s)'),
        ('import_specific_order', 'Import Specific Order(s)'),
        ('export_invoice_information', 'Export Invoice Information'),
        ('import_product_taxclass', 'Import Product TaxClass')
    ], string='Import/ Export Operations', help='Import/ Export Operations')

    start_date = fields.Datetime(string="From Date", help="From date.")
    end_date = fields.Datetime("To Date", help="To date.")
    import_specific_sale_order = fields.Char(
        string="Sale Order Reference",
        help="You can import Magento Order by giving order number here,Ex.000000021 \n "
             "If multiple orders are there give order number comma (,) seperated "
    )
    import_specific_product = fields.Char(
        string='Product Reference',
        help="You can import Magento prduct by giving product sku here, Ex.24-MB04 \n "
             "If Multiple product are there give product sku comma(,) seperated"
    )
    datas = fields.Binary(string="Choose File", filters="*.csv")
    file_name = fields.Char(string='Name')
    export_method = fields.Selection([
        ("direct", "Export in Magento Layer"), ("csv", "Export in CSV file"),
        ("xlsx", "Export in XLSX file")
    ], default="direct")
    do_not_update_existing_product = fields.Boolean(
        string="Do not update existing Products?",
        help="If checked and Product(s) found in odoo/magento layer, then not update the Product(s)"
    )
    auto_validate_stock = fields.Boolean(
        string="Auto validate inventory?",
        help="If checked then all product stock will automatically validate"
    )

    @api.onchange('operations')
    def on_change_operation(self):
        """
        Set end date when change operations
        """
        if self.operations == "import_products" or self.operations == "import_sale_order":
            self.start_date = datetime.today() - timedelta(days=10)
            self.end_date = datetime.now()
        else:
            self.start_date = None
            self.end_date = None

    def execute(self):
        """
        Execute different Magento operations based on selected operation,
        """
        magento_instance = self.env['magento.instance']
        magento_order_data_queue_obj = self.env['magento.order.data.queue.ept']
        magento_customer_data_queue_obj = self.env['magento.customer.data.queue.ept']
        magento_import_product_queue_obj = self.env['sync.import.magento.product.queue']
        magento_inventory_locations_obj = self.env['magento.inventory.locations']
        magento_product_product = self.env['magento.product.product']
        account_move = self.env['account.move']
        product_attribute = self.env['magento.attribute.set.ept']
        picking = self.env['stock.picking']
        message = ''
        if self.magento_instance_ids:
            instances = self.magento_instance_ids
        else:
            instances = magento_instance.search([])

        if self.operations == 'import_customer':
            for instance in instances:
                magento_customer_data_queue_obj.magento_create_customer_data_queues(
                    magento_instance=instance)
        elif self.operations == 'map_products':
            if not self.datas:
                raise Warning(_("Please Upload File to Continue Mapping Products..."))
            if os.path.splitext(self.file_name)[1].lower() not in ['.csv', '.xls', '.xlsx']:
                raise ValidationError(
                    _("Invalid file format. You are only allowed to upload .csv, .xls or .xlsx "
                      "file."))
            for instance in instances:
                if os.path.splitext(self.file_name)[1].lower() == '.csv':
                    self.import_magento_csv(instance.id)
                else:
                    self.import_magento_xls()
        elif self.operations == 'import_sale_order':
            order_queue_data = False
            for instance in instances:
                order_queue_data = magento_order_data_queue_obj.magento_create_order_data_queues(instance, self.start_date, self.end_date)

            result = {
                'name': _('Magento Order Data Queue'),
                'res_model': 'magento.order.data.queue.ept',
                'type': 'ir.actions.act_window',
            }
            if order_queue_data and order_queue_data.get('count') == 1:
                view_ref = self.env['ir.model.data'].get_object_reference(
                    'odoo_magento2_ept', 'view_magento_order_data_queue_ept_form'
                )
                view_id = view_ref[1] if view_ref else False
                result.update({
                    'views': [(view_id, 'form')],
                    'view_mode': 'form',
                    'view_id': view_id,
                    'res_id': order_queue_data.get('order_queue').id,
                    'target': 'current'
                })
            else:
                result.update({
                    'view_mode': 'tree,form',
                    'domain': "[('state', '!=', 'completed' )]"
                })
            return result
        elif self.operations == 'import_specific_order':
            if not self.import_specific_sale_order:
                raise Warning(_("Please enter Magento sale order Reference for performing this operation."))
            sale_order_list = self.import_specific_sale_order.split(',')
            for instance in instances:
                magento_order_data_queue_obj.import_specific_order(instance, sale_order_list)
            return {
                'name': _('Magento Specific Order Queue'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'magento.order.data.queue.ept',
                'type': 'ir.actions.act_window',
                'domain': "[('state', '!=', 'completed' )]",
            }
        elif self.operations == 'import_products':
            from_date = datetime.strftime(self.start_date, MAGENTO_DATETIME_FORMAT) if self.start_date else None
            to_date = datetime.strftime(self.end_date, MAGENTO_DATETIME_FORMAT) if self.end_date else None
            product_queue = False
            is_update = self.do_not_update_existing_product
            for instance in instances:
                product_queue = magento_import_product_queue_obj.create_sync_import_magento_product_queues(
                    instance, from_date, to_date, is_update)
            if product_queue:
                return {
                    'name': _('Magento Product Queue'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'sync.import.magento.product.queue',
                    'type': 'ir.actions.act_window',
                    'domain': "[('state', '!=', 'completed' )]",
                }
            else:
                message = 'No products are updated in these date range'
        elif self.operations == 'import_specific_product':
            if not self.import_specific_product:
                raise Warning(_("Please enter Magento product SKU for performing this operation."))
            product_sku_lists = self.import_specific_product.split(',')
            exist_log_ids = []
            is_update = self.do_not_update_existing_product
            for instance in instances:
                magento_import_product_queue_obj.import_specific_product(
                    instance, product_sku_lists,exist_log_ids, is_update)
            return {
                'name': _('Magento Specific Product Queue'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sync.import.magento.product.queue',
                'type': 'ir.actions.act_window',
                'domain': "[('state', '!=', 'completed' )]",
            }
        elif self.operations == 'import_product_stock':
            for instance in instances:
                if not instance.is_import_product_stock:
                    raise Warning(_("You are trying to import product stock."
                                    "But your configuration for the imported stock is disabled for this instance."
                                    "Please enable it and try it again."))
                if instance.magento_version in ['2.1', '2.2'] or not instance.is_multi_warehouse_in_magento:
                    # product_ids = magento_product_product.search([('magento_instance_id', '=', instance.id)])
                    magento_product_product.create_product_inventory(instance, self.auto_validate_stock)
                else:
                    inventory_locations = magento_inventory_locations_obj.search([
                        ('magento_instance_id', '=', instance.id)])
                    magento_product_product.create_product_multi_inventory(
                        instance, inventory_locations, self.auto_validate_stock)
        elif self.operations == 'import_product_taxclass':
            for instance in instances:
                instance.import_tax_class()
        elif self.operations == 'import_product_categories':
            for instance in instances:
                self.env['magento.product.category.ept'].get_all_category(instance)
        elif self.operations == 'import_product_attributes':
            for instance in instances:
                product_attribute.import_magento_product_attribute_set(instance)
        elif self.operations == 'export_shipment_information':
            picking.export_shipment_to_magento(instances)
            for instance in instances:
                instance.last_order_status_update_date = datetime.now()
        elif self.operations == 'export_invoice_information':
            account_move.export_invoice_to_magento(instances)
        elif self.operations == 'export_product_stock':
            for instance in instances:
                if instance.magento_version in ['2.1', '2.2'] or not instance.is_multi_warehouse_in_magento:
                    magento_product_product.export_multiple_product_stock_to_magento(instance)
                else:
                    inventory_locations = magento_inventory_locations_obj.search([
                        ('magento_instance_id', '=', instance.id)])
                    magento_product_product.export_product_stock_to_multiple_locations(
                        instance, inventory_locations)
                instance.last_update_stock_time = datetime.now()
        title = [vals for key, vals in self._fields['operations'].selection if key == self.operations]
        return {
            'effect': {
                'fadeout': 'slow',
                'message': " {} Process Completed Successfully! {}".format(title[0], message),
                'img_url': '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def prepare_product_for_export_in_magento(self):
        """
        This method is used to export products in Magento layer as per selection.
        If "direct" is selected, then it will direct export product into Magento layer.
        If "csv" is selected, then it will export product data in CSV file, if user want to do some
        modification in name, description, etc. before importing into Magento.
        """
        active_template_ids = self._context.get("active_ids", [])
        templates = self.env["product.template"].browse(active_template_ids)
        product_templates = templates.filtered(lambda template: template.type != "service")
        if not product_templates:
            raise UserError(_("It seems like selected products are not Storable products."))
        if self.export_method == "direct":
            self.prepare_product_for_magento(product_templates)
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': " 'Export in Magento Layer' Process Completed Successfully! {}".format(""),
                    'img_url': '/web/static/src/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        else:
            return self.export_product_for_magento(product_templates)

    def export_product_for_magento(self, odoo_templates):
        """
        Create and download CSV file for export product in Magento.
        :param odoo_templates: Odoo product template object
        """
        data = str()
        product_dic = []
        for instance in self.magento_instance_ids:
            for odoo_template in odoo_templates:
                if len(odoo_template.product_variant_ids.ids) == 1 and not odoo_template.default_code:
                    continue
                for variant in odoo_template.product_variant_ids.filtered(
                        lambda variant: variant.default_code != False):
                    row = self.prepare_data_for_export_to_csv_ept(odoo_template, variant, instance)
                    product_dic.append(row)
        if not product_dic:
            raise UserError(
                _('No data found to be exported.\n\nPossible Reasons:\n   - SKU(s) are not set properly.'))
        if self.export_method:
            # Based on customer's selected file format apply to call method
            method_name = "_export_{}".format(self.export_method)
            if hasattr(self, method_name):
                data = getattr(self, method_name)(product_dic)
        self.write({'datas': data.get('file')})
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=magento.import.export.ept&'
                   'field=datas&id=%s&filename=%s' % (
                       self.id, data.get('file_name')),
            'target': 'self',
        }

    def _export_csv(self, products):
        '''
        This method use for export selected product in CSV file for Map product
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        '''
        buffer = StringIO()
        csv_writer = DictWriter(buffer, list(products[0].keys()), delimiter=',')
        csv_writer.writer.writerow(list(products[0].keys()))
        csv_writer.writerows(products)
        buffer.seek(0)
        file_data = buffer.read().encode("utf-8")
        b_data = base64.b64encode(file_data)
        filename = 'magento_product_export_{}_{}.csv'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    def _export_xlsx(self, products):
        '''
        This method use for export selected product in CSV file for Map product
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        '''
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Map Product')
        header = list(products[0].keys())
        header_format = workbook.add_format({'bold': True, 'font_size': 10})
        general_format = workbook.add_format({'font_size': 10})
        worksheet.write_row(0, 0, header, header_format)
        index = 0
        for product in products:
            index += 1
            worksheet.write_row(index, 0, list(product.values()), general_format)
        workbook.close()
        b_data = base64.b64encode(output.getvalue())
        filename = 'magento_product_export_{}_{}.xlsx'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    @staticmethod
    def prepare_data_for_export_to_csv_ept(odoo_template, variant, instance):
        """
        Prepare data for Export Operations at map Odoo Products csv with Magento Products.
        :param odoo_template: product.template()
        :param variant: product.product()
        :param instance: magento.instance()
        :return: dictionary
        """
        position = 0
        return {
            'product_template_id': odoo_template.id,
            'product_id': variant.id,
            'template_name': odoo_template.name,
            'product_name': variant.name,
            'product_default_code': variant.default_code,
            'magento_sku': variant.default_code,
            'description': variant.description or "",
            'sale_description': odoo_template.description_sale if position == 0 and odoo_template.description_sale else '',
            'instance_id': instance.id
        }

    def prepare_product_for_magento(self, odoo_templates):
        """
        Add product and product template into Magento.
        :param odoo_templates: Odoo product template object
        :return:
        """
        magento_sku_missing = {}
        product_dict = {}
        for instance in self.magento_instance_ids:
            product_dict.update({'instance_id': instance.id})
            for odoo_template in odoo_templates:
                product_dict.update({'product_template_id': odoo_template.id})
                magento_sku_missing = self.mapped_magento_products(product_dict, magento_sku_missing)
        if magento_sku_missing:
            raise UserError(_('Missing Internal References For %s', str(list(magento_sku_missing.values()))))
        return True

    def import_magento_csv(self, instance_id):
        """
        Import CSV file and add product and product template into magento.
        :param instance: instance of magento.
        """
        magento_sku_missing = {}
        csv_reader = csv.DictReader(StringIO(base64.b64decode(self.datas).decode()), delimiter=',')
        for product_dict in csv_reader:
            if int(product_dict.get('instance_id')) == instance_id:
                magento_sku_missing = self.mapped_magento_products(product_dict, magento_sku_missing)
        return magento_sku_missing

    def import_magento_xls(self):
        """
        This method use for Read all data from XLS/XLSX file
        :return: Missing magento sku which is not set or any errors
        """
        magento_sku_missing = {}
        sheets = xlrd.open_workbook(file_contents=base64.b64decode(self.datas.decode('UTF-8')))
        header = dict()
        is_header = False
        for sheet in sheets.sheets():
            for row_no in range(sheet.nrows):
                if not is_header:
                    headers = [d.value for d in sheet.row(row_no)]
                    [header.update({d: headers.index(d)}) for d in headers]
                    is_header = True
                    continue
                row = dict()
                [row.update({k: sheet.row(row_no)[v].value}) for k, v in header.items() for c in
                 sheet.row(row_no)]
                magento_sku_missing = self.mapped_magento_products(row, magento_sku_missing)
        return magento_sku_missing

    def mapped_magento_products(self, product_dict, magento_sku_missing):
        """
        Map Odoo products with Magento Products
        :param product_dict: dict of line from product csv file
        :param magento_sku_missing: dictionary of lines where magento sku is not set.
        :return: dict of missing magento sku
        """
        if not product_dict.get('product_id'):
            odoo_template = self.env['product.template'].browse(int(product_dict.get('product_template_id')))
            for variant in odoo_template.product_variant_ids:
                product_dict.update({'magento_sku': variant.default_code})
                magento_sku_missing = self.create_or_update_magento_product_variant(product_dict, variant,
                                                                                    magento_sku_missing)
        else:
            odoo_product = self.env['product.product'].browse(int(product_dict.get('product_id')))
            magento_sku_missing = self.create_or_update_magento_product_variant(product_dict, odoo_product,
                                                                                magento_sku_missing)
        if magento_sku_missing:
            self._cr.commit()
        return magento_sku_missing

    def create_or_update_magento_product_template(self, product_dict, product):
        """
        Create or update magento product template when import product using CSV.
        :param product_dict: dict of csv file line
        :return: Magento Product Template Object
        """
        magento_template_object = self.env['magento.product.template']
        template_domain = self.prepare_magento_template_search_domain(product_dict, product)
        magento_template = magento_template_object.search(template_domain)
        if not magento_template:
            odoo_template = self.env['product.template'].browse(int(product_dict.get('product_template_id')))
            template_vals = self.prepare_magento_product_template_vals_ept(product_dict, odoo_template)
            magento_template = magento_template_object.create(template_vals)
            self.create_magento_template_images(magento_template, odoo_template)
        return magento_template

    @staticmethod
    def prepare_magento_template_search_domain(product_dict, product):
        if len(product.product_tmpl_id.product_variant_ids) > 1:
            return [('magento_instance_id', '=', int(product_dict.get('instance_id'))),
                    ('odoo_product_template_id', '=', int(product_dict.get('product_template_id')))]
        else:
            return [('magento_instance_id', '=', int(product_dict.get('instance_id'))),
                    # ('odoo_product_template_id', '=', int(product_dict.get('product_template_id'))),
                    ('magento_sku', '=', product_dict.get('magento_sku'))]

    @staticmethod
    def prepare_magento_product_template_vals_ept(product_dict, odoo_template):
        return {
            'magento_instance_id': product_dict.get('instance_id'),
            'odoo_product_template_id': product_dict.get('product_template_id'),
            'product_type': 'configurable' if odoo_template.product_variant_count > 1 else 'simple',
            'magento_product_name': odoo_template.name,
            'description': odoo_template.description,
            'short_description': odoo_template.description_sale,
            'magento_sku': False if odoo_template.product_variant_count > 1 else product_dict.get('magento_sku')
        }

    def create_or_update_magento_product_variant(self, product_dict, product, magento_sku_missing):
        """
        Create or update Magento Product Variant when import product using CSV.
        :param product_dict: dict {}
        :param product: product.product()
        :param magento_sku_missing: Missing SKU dictionary
        :return: Missing SKU dictionary
        """
        magento_product_object = self.env['magento.product.product']
        magento_prod_sku = product_dict.get('magento_sku')
        if not product_dict.get('magento_sku', False) and product.default_code:
            magento_prod_sku = product.default_code
        if not magento_prod_sku or magento_prod_sku == 'False':
            magento_sku_missing.update({product.id: product.name})
        else:
            domain = self.prepare_domain_for_magento_product_ept(product_dict, product)
            magento_variant = magento_product_object.search(domain)
            if not magento_variant:
                magento_template = self.create_or_update_magento_product_template(product_dict, product)
                prod_vals = self.prepare_magento_product_vals_ept(product_dict, product, magento_template,
                                                                  magento_prod_sku)
                magento_product = magento_product_object.create(prod_vals)
                self.create_magento_product_images(magento_template, product, magento_product)
            # else:
            #   magento_variant.write({'magento_sku': magento_prod_sku})
        return magento_sku_missing

    @staticmethod
    def prepare_domain_for_magento_product_ept(product_dict, product):
        """
        Prepare Domain for Search Magento Products
        :param product_dict: dict
        :param product: product.product()
        :return: list(tuple())
        """
        return [('magento_instance_id', '=', int(product_dict.get('instance_id'))),
                # ('odoo_product_id', '=', product.id),
                ('magento_sku', '=', product_dict.get('magento_sku'))]

    @staticmethod
    def prepare_magento_product_vals_ept(product_dict, product, magento_template, magento_prod_sku):
        return {
            'magento_instance_id': product_dict.get('instance_id'),
            'odoo_product_id': product.id,
            'magento_tmpl_id': magento_template.id,
            'magento_sku': magento_prod_sku,
            'description': product.description,
            'short_description': product.description_sale,
            'magento_product_name': product.name
        }
    def download_sample_attachment(self):
        """
        This Method relocates download sample file of internal transfer.
        :return: This Method return file download file.
        """
        attachment = self.env['ir.attachment'].search([('name', '=', 'magento_product_export.csv')])
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    def create_magento_template_images(self, magento_template, odoo_template):
        """ This method is use to create images in Woo layer.
            @param : self,woo_template
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
            Task_id: 165896
        """
        magento_product_image_obj = self.env["magento.product.image"]
        magento_product_image_list = []
        for odoo_image in odoo_template.ept_image_ids.filtered(lambda x: not x.product_id):
            magento_product_image = magento_product_image_obj.search(
                [("magento_tmpl_id", "=", magento_template.id),
                 ("odoo_image_id", "=", odoo_image.id)])
            if not magento_product_image:
                magento_product_image_list.append({
                    "odoo_image_id": odoo_image.id,
                    "magento_tmpl_id": magento_template.id,
                    'url': odoo_image.url,
                    'image': odoo_image.image,
                    'magento_instance_id': magento_template.magento_instance_id.id
                })
        if magento_product_image_list:
            magento_product_image_obj.create(magento_product_image_list)

    def create_magento_product_images(self, magento_template, odoo_product, magento_product):
        """ This method is use to create images in Woo layer.
            @param : self,woo_template
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
            Task_id: 165896
        """
        magento_product_image_obj = self.env["magento.product.image"]
        magento_product_image_list = []
        for odoo_image in odoo_product.ept_image_ids:
            magento_product_image = magento_product_image_obj.search(
                [("magento_tmpl_id", "=", magento_template.id),
                 ("magento_product_id", "=", magento_product.id),
                 ("odoo_image_id", "=", odoo_image.id)])
            if not magento_product_image:
                magento_product_image_list.append({
                    "odoo_image_id": odoo_image.id,
                    "magento_tmpl_id": magento_template.id,
                    "magento_product_id": magento_product.id if magento_product else False,
                    'url': odoo_image.url,
                    'image': odoo_image.image,
                    'magento_instance_id': magento_template.magento_instance_id.id
                })
        if magento_product_image_list:
            magento_product_image_obj.create(magento_product_image_list)
