#!/usr/bin/python3
"""
Describes methods for sync/ Import product queues.
"""
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import Warning
from .api_request import req, create_search_criteria
from ..python_library.php import Php

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class SyncImportMagentoProductQueue(models.Model):
    """
    Describes sync/ Import product queues.
    """
    _name = "sync.import.magento.product.queue"
    _description = "Sync/ Import Product Queue"
    name = fields.Char(help="Sequential name of imported/ Synced products.", copy=False)
    magento_instance_id = fields.Many2one(
        'magento.instance',
        string='Instance',
        help="Product imported from or Synced to this Magento Instance."
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed')
    ], default='draft', copy=False, help="Status of Order Data Queue")
    import_product_common_log_book_id = fields.Many2one(
        "common.log.book.ept",
        help="Related Log book which has all logs for current queue."
    )
    import_product_common_log_lines_ids = fields.One2many(
        related="import_product_common_log_book_id.log_lines",
        help="Log lines of Common log book for particular product queue"
    )
    import_product_queue_line_ids = fields.One2many(
        "sync.import.magento.product.queue.line",
        "sync_import_magento_product_queue_id",
        help="Sync/ Import product queue line ids"
    )
    import_product_queue_line_total_record = fields.Integer(
        string='Total Records',
        compute='_compute_product_queue_line_record',
        help="Returns total number of Sync/Import product queue lines"
    )
    import_product_queue_line_draft_record = fields.Integer(
        string='Draft Records',
        compute='_compute_product_queue_line_record',
        help="Returns total number of draft Sync/Import product queue lines"
    )
    import_product_queue_line_fail_record = fields.Integer(
        string='Fail Records',
        compute='_compute_product_queue_line_record',
        help="Returns total number of Failed Sync/Import product queue lines"
    )
    import_product_queue_line_done_record = fields.Integer(
        string='Done Records',
        compute='_compute_product_queue_line_record',
        help="Returns total number of done Sync/Import product queue lines"
    )

    def _compute_product_queue_line_record(self):
        """
        This will calculate total, draft, failed and done products sync/import from ebay.
        """
        for product_queue in self:
            product_queue.import_product_queue_line_total_record = len(
                product_queue.import_product_queue_line_ids
            )
            product_queue.import_product_queue_line_draft_record = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'draft')
            )
            product_queue.import_product_queue_line_fail_record = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'failed')
            )
            product_queue.import_product_queue_line_done_record = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'done')
            )

    def action_sync_import_product_queue_record_count(self):
        """
        This method used to display the order queue records. you can see the record here: Ebay
        => Catalog => Import Product Queue Data
        :return:
        """
        return True

    @api.model
    def create(self, vals):
        """
        Creates a sequence for Ordered Data Queue
        :param vals: values to create Ordered Data Queue
        :return: SyncImportMagentoProductQueue Object
        """
        sequence_id = self.env.ref('odoo_magento2_ept.magento_seq_import_product_queue_data').ids
        if sequence_id:
            record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
        else:
            record_name = '/'
        vals.update({'name': record_name or ''})
        return super(SyncImportMagentoProductQueue, self).create(vals)

    def create_sync_import_magento_product_queues(self, instance, from_date, to_date, is_update=True):
        """
        Creates product queues when sync/ import products from Magento.
        :param instance: current instance of Magento
        :param from_date:  Sync product start from this date
        :param to_date: Sync product end to this date
        :return:
        """
        product_queue = False
        product_queue_line = self.env["sync.import.magento.product.queue.line"]
        filters = {'updated_at': {'to': to_date}, 'status': 1}
        if from_date:
            filters.get('updated_at', dict()).update({'from': from_date})
        product_types = {'configurable', 'simple'}
        for product_type in product_types:
            filters.update({'type_id': product_type})
            response = self.get_products_api_response_from_magento(instance, filters)
            if response.get('total_count') == 0 or not response.get('items'):
                instance.magento_import_product_page_count = 1
                continue
            product_queue = product_queue_line.create_import_magento_product_queue_line(
                response.get('items', False), instance, is_update)
            total_imported_products = instance.magento_import_product_page_count * 200

            instance.magento_import_product_page_count += 1 # product_page_count

            while total_imported_products <= response.get('total_count'):
                response = self.get_products_api_response_from_magento(instance, filters)
                if not response.get('items'):
                    instance.magento_import_product_page_count = 1
                    break
                product_queue = product_queue_line.create_import_magento_product_queue_line(response.get('items', False), instance, is_update)
                total_imported_products = instance.magento_import_product_page_count * 200
                instance.magento_import_product_page_count += 1 # product_page_count
                self._cr.commit()
        instance.last_product_import_date = datetime.now()
        return product_queue

    def get_products_api_response_from_magento(self, instance, filters):
        search_criteria = create_search_criteria(filters)
        search_criteria['searchCriteria']['pageSize'] = 200
        search_criteria['searchCriteria']['currentPage'] = instance.magento_import_product_page_count
        query_string = Php.http_build_query(search_criteria)
        try:
            api_url = '/V1/products?%s'%query_string
            response = req(instance, api_url)
        except Exception as error:
            raise Warning(_("Error while requesting products {}".format(error)))
        return response

    def import_specific_product(self, instance, product_sku_lists,exist_log_ids, is_update=True):
        """
        Creates product queues when sync/ import products from Magento.
        :param instance: current instance of Magento
        :param product_sku_lists:  Dictionary of Product SKUs
        :return:
        """
        product_queue_line = self.env["sync.import.magento.product.queue.line"]
        product_queue_data = {'product_queue': False, 'count': 0}
        log_line_id = []
        for product_sku in product_sku_lists:
            try:
                sku = Php.quote_sku(product_sku)
                api_url = '/V1/products/{}'.format(sku)
                response = req(instance, api_url)
            except Exception as error:
                if len(product_sku_lists) > 1:
                    common_log_line_obj = self.env['common.log.lines.ept']
                    log_line = common_log_line_obj.create({
                        'message': "Magento Product Not found for SKU : '%s'" % product_sku,
                        'default_code' : product_sku
                    })
                    log_line_id.append(log_line.id)
                    continue
                else:
                    raise UserError(_("Error while requesting products" + str(error)))
                #raise Warning(_("Error while requesting product Sku {}. Make sure that the product is exist in Magento.").format(product_sku))
            if response:
                product_queue_data = product_queue_line.create_import_specific_product_queue_line(
                    response, instance, product_queue_data, is_update)
        instance.last_product_import_date = datetime.now()
        if log_line_id:
            product_queue = product_queue_data.get('product_queue')
            common_log_obj = self.env["common.log.book.ept"].create({
                'type': 'import',
                'module': 'magento_ept',
                'magento_instance_id': instance.id,
                'active': True,
                'model_id': self.env["common.log.lines.ept"].get_model_id("magento.product.product"),
                "log_lines": [(6, 0, log_line_id)]
            })
            exist_log_ids.append(common_log_obj.id)
            if product_queue:
                product_queue.import_product_common_log_book_id = common_log_obj
        return True
